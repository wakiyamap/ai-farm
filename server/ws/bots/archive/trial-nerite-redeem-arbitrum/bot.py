"""trial-nerite-redeem-arbitrum: USND below-par redemption on Nerite (Liquity V2 fork, Arbitrum), one atomic executor call.

The gain appears when the DEX price of ETH runs ahead of the price Nerite redeems at (measured: USND pool price and
redemption fee flat, WETH/USDC +1.4% in 2 min before a take; the WETH branch reads a push oracle whose answer was
18 min old at a take), and the incumbent takes it 5-15 s later. So the bot simulates the executor take() on a 30 s
timer (and on Swap events of the USND/USDC pool through the feed), switches to a 2 s timer for a bounded time once
the simulation shows a gain of 0.01 USDC or more, and, when the simulated USDC gain exceeds the
signed gas cap, sends it (BOT_MODE=live) or logs a paper simulation (BOT_MODE=paper). The executor reverts unless
its USDC balance grows by minProfit, so a lost attempt costs gas only.
"""
import datetime
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.append('/opt/farm/lib')   # farmbot_signer lives here; the live service does not add it

HERE = Path(__file__).resolve().parent
MODE = os.environ.get('BOT_MODE', 'paper')
LANE = os.environ.get('RPC_LANE', 'paper')
RELAY = os.environ['RPC_RELAY_URL'].rstrip('/')
CHAIN = 'arbitrum'
FEED = 'http://127.0.0.1:8546/logs/arbitrum'

# Addresses: read from the incumbent's take 0x0b1ac32b... (receipt logs) and the registry getters, see README.
FLASH_POOL = '0x319b7186c838509ebf41f44ea348b2b5345254c2'   # Uniswap V3 USND/USDC pool
USND = '0x4ecf61a6c2fab8a047ceb3b3b263b401763e9d49'         # registry.boldToken()
USDC = '0xaf88d065e77c8cc2239327c5edb3a432268e5831'         # native USDC, 6 decimals
REGISTRY = '0x7f7fbc2711c0d6e8ef757dbb82038032dd168e68'     # Nerite CollateralRegistry
WETH = '0x82af49447d8a07e3bd95bd0d56f35241523fbab1'
WETH_USDC = '0xc6962004f452be9203591991d15f6b388e09e8d0'    # Uniswap V3 WETH/USDC 0.05%
WETH_TM = '0x56698cd47d5194c2b7f947ac8370b3cb7359e709'      # registry.getTroveManager(0), emits Redemption
LEGS = (   # (collateral, Uniswap V3 pool collateral/WETH); a collateral with a zero balance is skipped on-chain
    ('0x5979d7b546e38e414f7e9822514be443a4800529', '0x35218a1cbac5bbc3e57fd9bd38219d37571b3537'),   # wstETH
    ('0x4186bfc76e2e237523cbc30fd220fe055156b41f', '0x48b0ab72c2591849e678e7d6f272b75ef9b863f7'),   # rsETH
    ('0x35751007a407ca6feffe80b3cb397736d2cf4dbe', '0xa169d1ab5c948555954d38700a6cdaa7a4e0c3a0'),   # weETH
    ('0x6c84a8f1c29108f47a79964b5fe888d4f4d0de40', '0xcb198a55e2a88841e855be4eacaad99422416b33'),   # tBTC
)
MAX_ITER = 10
MAX_FEE_PCT = 10**18
SWAP_TOPIC = '0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67'     # V3 Swap
REDEEM_TOPIC = '0x84ec8e1674d62e3a8ff294b1a7f53527d2d10291765fadf94e0ce431b2334334'   # TroveManager Redemption
# take((address,address,address,uint256,address,uint256,uint256,address,address,(address,address)[]),uint256)
SEL_TAKE = '0xbab11f33'
SEL_SLOT0 = '0x3850c7bd'

PAPER_EXEC = '0xb464f7314d55ec6a9a0cf6f7f6df17af8ed5b352'   # fork deployment; paper code override only
PAPER_OWNER = '0xc0ffee0000000000000000000000000000000001'
EXEC = os.environ.get('EXECUTOR_ADDR_ARBITRUM') or os.environ.get('EXECUTOR_ADDR')
if MODE == 'live' and not EXEC:
    raise SystemExit('EXECUTOR_ADDR_ARBITRUM or EXECUTOR_ADDR is required in live mode')
RUNTIME = (HERE / 'executor-runtime.hex').read_text().strip()
if not RUNTIME.startswith('0x') or len(RUNTIME) < 100:
    raise SystemExit('missing paper executor runtime')

LOG = HERE / 'logs' / 'bot.jsonl'
STATE = HERE / 'state' / 'state.json'
CU_FILE = HERE / 'state' / 'cu.json'
LOG.parent.mkdir(exist_ok=True)
STATE.parent.mkdir(exist_ok=True)

# ---- loss guard -----------------------------------------------------------------------------
MAX_TX_USD = 0.90              # signed gas cap (maxFee x gasLimit) stays under this
MAX_FEE_WEI = 100_000_000      # 0.1 gwei absolute ceiling for maxFeePerGas (base fee is 0.02 gwei)
MAX_GAS_LIMIT = 4_500_000      # the incumbent's takes use 2.79m-2.90m
SIM_GAS = 6_000_000
GAS_MARGIN_NUM, GAS_MARGIN_DEN = 11, 10    # gas limit = eth_estimateGas x 1.10
BASE_FEE_HEADROOM_PCT = 5      # maxFeePerGas = latest base fee x 1.05 + TIP_WEI
TIP_WEI = 1                    # Arbitrum orders first come first served; a tip buys nothing. Never 0 (signer)
ROUGH_GAS = 2_900_000          # only for the cheap pre-filter before an estimate is made
PROBE_USND = 40                # the incumbent's size; the pool is thin, the fork sweep peaks at 40
SIZES_USND = (30, 40, 50)       # flash-swapped out of the pool, never the bot's own funds
POLL_INTERVAL = 30             # base timer: one eth_call probe (26 CU) = 75k CU/day
FAST_INTERVAL = 2              # timer while a gain is visible
FAST_FLOOR = 10_000            # micro-USDC of probe gain that starts or extends fast mode
FAST_HOLD = 40                 # seconds fast mode lasts after the last probe at or above FAST_FLOOR
FAST_CU_BUDGET = 15_000        # relay CU per UTC day spent in fast mode; after that the base timer only
PX_CACHE_SECONDS = 20          # ETH price and base fee reuse for the pre-filter only
SEND_COOLDOWN = 60
RELAY_CU_CAP = 93_000          # per UTC day, base + fast + sends; the feed's own CU is metered separately
CU_COST = {'eth_call': 26, 'eth_estimateGas': 20, 'eth_getLogs': 75, 'eth_getTransactionReceipt': 20,
           'eth_blockNumber': 10, 'eth_getBlockByNumber': 20}
_id = 0
_fast = {'on': False, 'spent': 0}   # fast-mode flag and today's fast-mode CU (set by rpc())


class ReadBudgetExceeded(Exception):
    pass


def log(ev, **kw):
    row = {'ts': round(time.time(), 3), 'ev': ev, **kw}
    with LOG.open('a') as f:
        f.write(json.dumps(row, separators=(',', ':'), default=str) + '\n')


def rpc(method, params):
    global _id
    day = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    try:
        budget = json.loads(CU_FILE.read_text())
    except Exception:
        budget = {'day': day, 'cu': 0}
    if budget.get('day') != day:
        budget = {'day': day, 'cu': 0}
    cost = CU_COST.get(method, 26)
    if budget['cu'] + cost > RELAY_CU_CAP:
        raise ReadBudgetExceeded(f'{RELAY_CU_CAP} relay CU/day bot cap reached')
    budget['cu'] += cost
    if _fast['on']:
        budget['fast_cu'] = budget.get('fast_cu', 0) + cost
    _fast['spent'] = budget.get('fast_cu', 0)
    CU_FILE.write_text(json.dumps(budget))
    _id += 1
    body = json.dumps({'jsonrpc': '2.0', 'id': _id, 'method': method, 'params': params}).encode()
    req = urllib.request.Request(f'{RELAY}/{CHAIN}?lane={LANE}', body, {'content-type': 'application/json'})
    with urllib.request.urlopen(req, timeout=30) as resp:
        ans = json.load(resp)
    if 'error' in ans:
        raise RuntimeError(f'{method}: {str(ans["error"])[:300]}')
    return ans['result']


def word(n):
    return format(n, '064x')


def aword(a):
    return a.lower().removeprefix('0x').zfill(64)


def bot_address():
    import farmbot_signer
    a = farmbot_signer.my_address()
    a = a.get('address') if isinstance(a, dict) else a   # my_address() returns {"ok":..., "address":...}
    if not isinstance(a, str) or len(a) != 42:
        raise RuntimeError('signer my_address returned no address')
    return a


def exec_ctx():
    if MODE == 'live':
        return bot_address(), EXEC, None
    return PAPER_OWNER, PAPER_EXEC, {PAPER_EXEC: {'code': RUNTIME}}


def calldata(amount_usnd_wei, min_profit):
    """ABI encoding of take(Route,uint256); Route ends with a dynamic (address,address)[] (checked against cast)."""
    route = (aword(FLASH_POOL) + aword(USND) + aword(USDC) + word(amount_usnd_wei) + aword(REGISTRY)
             + word(MAX_ITER) + word(MAX_FEE_PCT) + aword(WETH) + aword(WETH_USDC)
             + word(10 * 32)                      # offset of legs inside the Route tuple
             + word(len(LEGS)) + ''.join(aword(t) + aword(p) for t, p in LEGS))
    return SEL_TAKE + word(2 * 32) + word(min_profit) + route


def sim(data, ctx, gas=SIM_GAS):
    frm, to, ov = ctx
    params = [{'from': frm, 'to': to, 'data': data, 'gas': hex(gas)}, 'latest'] + ([ov] if ov else [])
    return int(rpc('eth_call', params)[2:66], 16)


def try_sim(data, ctx, gas=SIM_GAS):
    try:
        return sim(data, ctx, gas)
    except ReadBudgetExceeded:
        raise
    except RuntimeError:
        return None    # executor revert: the round trip does not pay (USND at or above its redemption value)


def estimate(data, ctx):
    frm, to, ov = ctx
    params = [{'from': frm, 'to': to, 'data': data}, 'latest'] + ([ov] if ov else [])
    return int(rpc('eth_estimateGas', params), 16)


def eth_usd():
    """USDC per WETH from slot0 of the WETH/USDC pool the route sells into (token0 = WETH, token1 = USDC)."""
    sqrt_p = int(rpc('eth_call', [{'to': WETH_USDC, 'data': SEL_SLOT0}, 'latest'])[2:66], 16)
    return sqrt_p * sqrt_p * 10**12 / 2**192


def winner_block(send_block, our_hash):
    """Block of the Redemption event near our send (ours if we won)."""
    head = int(rpc('eth_blockNumber', []), 16)
    logs = rpc('eth_getLogs', [{'address': WETH_TM, 'fromBlock': hex(max(0, send_block - 2400)), 'toBlock': hex(head),
                                'topics': [REDEEM_TOPIC]}])
    ours = [int(x['blockNumber'], 16) for x in logs if x['transactionHash'].lower() == our_hash.lower()]
    if ours:
        return min(ours), None
    if not logs:
        return None, None
    last = max(logs, key=lambda x: int(x['blockNumber'], 16))
    return int(last['blockNumber'], 16), last['transactionHash']


def send_live(data, gas_limit, max_fee, gross, min_profit, cap_usd, amount):
    import farmbot_signer
    reply = farmbot_signer.send(CHAIN, EXEC, data, 0, gas_limit, max_fee, max_priority_fee_per_gas=TIP_WEI)
    h = None
    if isinstance(reply, dict):
        h = reply.get('txHash') or reply.get('tx_hash') or reply.get('hash')
    if not h:
        log('signer_reject', reply=reply, amount_usnd=amount)   # final, never retried
        return
    log('send', hash=h, amount_usnd=amount, gas_limit=gas_limit, max_fee=max_fee, priority=TIP_WEI, gross_usdc=gross,
        min_profit_usdc=min_profit, gas_cap_usd=cap_usd, executor=EXEC)
    receipt = None
    for _ in range(30):
        time.sleep(1)
        try:
            receipt = rpc('eth_getTransactionReceipt', [h])
        except ReadBudgetExceeded:
            break
        except Exception:
            receipt = None
        if receipt:
            break
    if not receipt:
        log('send_result', hash=h, result='unknown', gas_used=None, winner_block=None)
        return
    b = int(receipt['blockNumber'], 16)
    status = int(receipt['status'], 16)
    used = int(receipt['gasUsed'], 16)
    cost = used * int(receipt['effectiveGasPrice'], 16)
    try:
        wb, wtx = winner_block(b, h)
    except Exception:
        wb, wtx = None, None
    log('send_result', hash=h, result='won' if status else 'lost', gas_used=used, gas_cost_wei=cost, send_block=b,
        winner_block=wb, winner_tx=wtx, blocks_after_winner=(b - wb if wb is not None else None),
        gross_usdc=gross, amount_usnd=amount)


def check(s, trigger):
    """One look at the chain. Returns the probe gain in micro-USDC (None = the round trip does not pay)."""
    now = time.time()
    s['last_check'] = now
    ctx = exec_ctx()
    probe = try_sim(calldata(PROBE_USND * 10**18, 0), ctx)
    if not probe:
        log('check', trigger=trigger, probe_gain=probe, reason='nothing_to_take')
        return probe
    px = s.get('px')
    if not px or now - px[0] > PX_CACHE_SECONDS:
        px = [now, eth_usd(), int(rpc('eth_getBlockByNumber', ['latest', False])['baseFeePerGas'], 16)]
        s['px'] = px
    price, base_fee = px[1], px[2]
    max_fee = base_fee + base_fee * BASE_FEE_HEADROOM_PCT // 100 + TIP_WEI
    rough_cap_usd = ROUGH_GAS * max_fee / 1e18 * price
    if probe / 1e6 < rough_cap_usd * 0.8:
        # far below any signable cap: no sweep, no estimate
        log('check', trigger=trigger, probe_gain=probe, rough_cap_usd=rough_cap_usd, base_fee=base_fee, eth_usd=price,
            reason='gain_below_gas')
        return probe
    # close to the cap: fresh price and base fee for everything that is signed
    price = eth_usd()
    base_fee = int(rpc('eth_getBlockByNumber', ['latest', False])['baseFeePerGas'], 16)
    s['px'] = [now, price, base_fee]
    max_fee = base_fee + base_fee * BASE_FEE_HEADROOM_PCT // 100 + TIP_WEI
    rows = {PROBE_USND: probe}
    for size in SIZES_USND:
        if size != PROBE_USND:
            rows[size] = try_sim(calldata(size * 10**18, 0), ctx)
    amount, gross = max(((k, v) for k, v in rows.items() if v), key=lambda x: x[1])
    try:
        est = estimate(calldata(amount * 10**18, 0), ctx)
    except RuntimeError as e:
        log('opportunity_skip', reason='estimate_revert', error=str(e)[:160], amount_usnd=amount, gross_usdc=gross)
        return probe
    gas_limit = est * GAS_MARGIN_NUM // GAS_MARGIN_DEN
    gross_usd = gross / 1e6
    cap_wei = gas_limit * max_fee
    cap_usd = cap_wei / 1e18 * price
    min_profit = int(cap_usd * 1e6) + 1          # a win always pays more than the signed gas cap
    log('opportunity', trigger=trigger, sweep=rows, amount_usnd=amount, gross_usdc=gross, gross_usd=gross_usd,
        eth_usd=price, base_fee=base_fee, gas_estimate=est, gas_limit=gas_limit, max_fee=max_fee, priority=TIP_WEI,
        gas_cap_usd=cap_usd, min_profit_usdc=min_profit)
    if max_fee > MAX_FEE_WEI or gas_limit > MAX_GAS_LIMIT or cap_usd >= MAX_TX_USD:
        log('opportunity_skip', reason='fee_gas_or_usd_cap', max_fee=max_fee, gas_limit=gas_limit, gas_cap_usd=cap_usd)
        return probe
    if gross_usd <= cap_usd or gross < min_profit:
        log('opportunity_skip', reason='gross_below_gas_cap', gross_usd=gross_usd, gas_cap_usd=cap_usd)
        return probe
    if s.get('cooldown_until', 0) > now:
        log('opportunity_skip', reason='cooldown')
        return probe
    data = calldata(amount * 10**18, min_profit)
    checked = try_sim(data, ctx, gas_limit)      # the exact guarded call at the signed gas limit
    if not checked:
        log('simulate_revert', amount_usnd=amount, min_profit_usdc=min_profit, gas_limit=gas_limit)
        return probe
    s['cooldown_until'] = now + SEND_COOLDOWN
    if MODE == 'live':
        send_live(data, gas_limit, max_fee, checked, min_profit, cap_usd, amount)
    else:
        log('paper_sim', result='success', amount_usnd=amount, gross_usdc=checked, min_profit_usdc=min_profit,
            gas_limit=gas_limit, max_fee=max_fee, priority=TIP_WEI, gas_cap_usd=cap_usd,
            net_usd_at_cap=checked / 1e6 - cap_usd)
    return probe


def load_state():
    try:
        return json.loads(STATE.read_text())
    except Exception:
        return {'feed_cursor': None, 'last_check': 0, 'cooldown_until': 0}


def save_state(s):
    tmp = STATE.with_suffix('.tmp')
    tmp.write_text(json.dumps(s, separators=(',', ':')))
    tmp.replace(STATE)


def feed_wait(cursor, timeout):
    q = {'address': FLASH_POOL, 'topic0': SWAP_TOPIC, 'timeout': str(timeout)}
    if cursor:
        q['after'] = cursor
    with urllib.request.urlopen(FEED + '?' + urllib.parse.urlencode(q), timeout=timeout + 10) as r:
        return json.load(r)


def after_check(s, gain):
    """Fast mode: on while a gain at or above FAST_FLOOR was seen in the last FAST_HOLD seconds and budget is left."""
    now = time.time()
    if gain and gain >= FAST_FLOOR:
        s['fast_until'] = now + FAST_HOLD
    want = s.get('fast_until', 0) > now and _fast['spent'] < FAST_CU_BUDGET
    if want != _fast['on']:
        log('fast_mode', on=want, probe_gain=gain, fast_cu_today=_fast['spent'])
    _fast['on'] = want


def main():
    s = load_state()
    s.pop('px', None)
    log('start', mode=MODE, executor=(EXEC if MODE == 'live' else PAPER_EXEC), pool=FLASH_POOL, registry=REGISTRY,
        poll_seconds=POLL_INTERVAL, fast_seconds=FAST_INTERVAL)
    while True:
        try:
            interval = FAST_INTERVAL if _fast['on'] else POLL_INTERVAL
            wait = interval - (time.time() - s.get('last_check', 0))
            if wait <= 0:
                after_check(s, check(s, 'fast' if _fast['on'] else 'timer'))
                save_state(s)
                continue
            if _fast['on']:
                time.sleep(wait)
                continue
            # base mode: the feed long-poll is the sleep; a pool swap or a gap triggers a check at once
            result = feed_wait(s.get('feed_cursor'), max(1, min(55, int(wait) + 1)))
            s['feed_cursor'] = result.get('cursor', s.get('feed_cursor'))
            if result.get('gap') or result.get('logs'):
                if time.time() - s.get('last_check', 0) >= 5:
                    after_check(s, check(s, 'gap' if result.get('gap') else 'pool_swap'))
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
            log('feed_error', error=str(e)[:180])   # 429/503/timeout: the timer keeps re-reading state
            time.sleep(min(30, max(1, POLL_INTERVAL - (time.time() - s.get('last_check', 0)))))
        except ReadBudgetExceeded as e:
            _fast['on'] = False
            log('read_budget', error=str(e))
            time.sleep(600)
        except Exception as e:
            log('loop_error', error=str(e)[:250])
            time.sleep(5)
        save_state(s)


if __name__ == '__main__':
    main()
