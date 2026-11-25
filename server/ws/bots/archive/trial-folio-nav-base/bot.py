"""trial-folio-nav-base: Reserve Folio (index token) redeem round trip on Base, one atomic executor call.

A Folio share (LCAP, "CF Large Cap Index") is redeemed for its basket by anyone with Folio.redeem(). When LCAP is cheap
in its Aerodrome Slipstream LCAP/USDC pool relative to the basket (cbBTC, WETH, cbXRP, cbADA, SOL, cbDOGE, HYPE), the
round trip WETH -> USDC -> LCAP -> redeem -> sell the six non-WETH basket tokens for WETH pays. Executor 0xb52603ce and
three smaller operators take it about 60 times a day for 0.02-0.2 USD each (README). The bot simulates the executor's
probe() on a timer and on every Swap of the LCAP/USDC pool (feed), sweeps the size when the route shows a gain, and,
when the simulated WETH gain exceeds the signed gas cap, sends it (BOT_MODE=live) or logs a paper simulation
(BOT_MODE=paper). The executor reverts unless its WETH balance grows by minProfit after the flash loan is repaid, so a
lost attempt costs gas only.
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
CHAIN = 'base'
FEED = 'http://127.0.0.1:8546/logs/base'

# Addresses: read from the incumbent's take (scratch/ic-76eb/trace-0xe52a9a05.json) and checked with
# token0()/token1()/fee()/factory()/symbol() getters and Folio.totalAssets() (scratch/ic-76eb/pools.py), see README.
VAULT = '0xba12222222228d8ba445958a75a0704d566bf2c8'        # Balancer V2 Vault, flash loan fee 0 (holds about 23 WETH)
WETH = '0x4200000000000000000000000000000000000006'
USDC = '0x833589fcd6edb6e08f4c7c32d4f71b54bda02913'
LCAP = '0x4da9a0f397db1397902070f93a4d6ddbc0e0e6e8'         # Reserve Folio "CF Large Cap Index"
CBBTC = '0xcbb7c0000ab88b473b1f5afd9ef808440eed33bf'
CBXRP = '0xcb585250f852c6c6bf90434ab21a00f02833a4af'
CBADA = '0xcbada732173e39521cdbe8bf59a6dc85a9fc7b8c'
SOL = '0x311935cd80b76769bf2ecc9d8ab7635b2139cf82'
CBDOGE = '0xcbd06e5a2b0c65597161de254aa074e489deb510'
HYPE = '0x15d0e0c55a3e7ee67152ad7e89acf164253ff68d'
WETH_USDC = '0xb4cb800910b228ed3d0834cf79d697127bbb00e5'    # Uniswap V3 WETH/USDC 0.01 pct
LCAP_USDC = '0xc8c15670050541255f9b797c008047682524861f'    # Aerodrome Slipstream LCAP/USDC, fee 0.3 pct
P_CBBTC = '0x5b3613ef9a535b48e82e2800acb77053dfec93b1'      # PancakeSwap V3 WETH/cbBTC 0.25 pct
P_CBXRP = '0xf0844016f0e92099d3d56ee13c6a50df59e08781'      # WETH/cbXRP, factory 0x9cb22058 (uniswapV3SwapCallback)
P_CBADA = '0xb862f23ba38c8c65e256782b31e8c08c9aefd612'      # Aerodrome Slipstream WETH/cbADA
P_SOL = '0xab07de353e15b80fa3b4224d5c8fdf3ac9f50670'        # PancakeSwap V3 SOL/WETH 0.05 pct
P_CBDOGE = '0x28138bfeaddc0f9ab6bb9303e67e2da17ff2a7e1'     # PancakeSwap V3 WETH/cbDOGE 0.25 pct
P_HYPE = '0x9e48d016ee76cf53e2de8dc8058c7549c8c202df'       # HYPE/WETH 0.05 pct, factory 0xade65c38 (uniswapV3SwapCallback)
Z = '0x0000000000000000000000000000000000000000'
# Step = (kind, target, tokenIn): 0 UniV3-style pool swap, 1 Folio redeem. Each step spends the executor's whole
# balance of tokenIn (a redeem burns the whole Folio share balance).
ROUTES = {
    # buy LCAP in its pool, redeem it for the basket, sell the basket (the incumbents' redeem direction)
    'lcap_redeem': [(0, WETH_USDC, WETH), (0, LCAP_USDC, USDC), (1, LCAP, Z), (0, P_CBBTC, CBBTC), (0, P_CBXRP, CBXRP),
                    (0, P_CBADA, CBADA), (0, P_SOL, SOL), (0, P_CBDOGE, CBDOGE), (0, P_HYPE, HYPE)],
}
SWAP_TOPIC = '0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67'     # Swap of Uniswap V3 and Slipstream pools
SEL_RUN = '0xe1fac79a'   # cast sig run(address,address,uint256,(uint8,address,address)[],uint256)
SEL_PROBE = '0x00b4a99a'  # cast sig probe(address,address,uint256,(uint8,address,address)[][])
PROBE_GAS = 30_000_000   # eth_call only: one reverted trial of about 1.5m gas per route

PAPER_EXEC = '0xb464f7314d55ec6a9a0cf6f7f6df17af8ed5b352'   # fork deployment; paper code override only
PAPER_OWNER = '0xc0ffee0000000000000000000000000000000001'
EXEC = os.environ.get('EXECUTOR_ADDR_BASE') or os.environ.get('EXECUTOR_ADDR')
if MODE == 'live' and not EXEC:
    raise SystemExit('EXECUTOR_ADDR_BASE or EXECUTOR_ADDR is required in live mode')
RUNTIME = (HERE / 'executor-runtime.hex').read_text().strip()
if not RUNTIME.startswith('0x') or len(RUNTIME) < 100:
    raise SystemExit('missing paper executor runtime')

LOG = HERE / 'logs' / 'bot.jsonl'
STATE = HERE / 'state' / 'state.json'
CU_FILE = HERE / 'state' / 'cu.json'
LOG.parent.mkdir(exist_ok=True)
STATE.parent.mkdir(exist_ok=True)

# ---- loss guard -----------------------------------------------------------------------------
# Base is an OP Stack chain: the L1 data fee and the operator fee are charged at inclusion and no signed field bounds
# them, so the only enforceable worst case of one send is the bot wallet's native balance. The trial limit is 1 USD
# per send, therefore the wallet itself stays under 1 USD: the manifest funds 0.75 USD, and take() refuses to sign
# while balance x ETH/USD is WALLET_MAX_USD or more (same guard as trial-peapods-arb-base, review 57f67367).
WALLET_MAX_USD = 0.95          # live: no send while the bot wallet's native balance is worth this much or more
SEL_SLOT0 = '0x3850c7bd'       # cast sig slot0(); read on WETH_USDC (token0 = WETH, token1 = USDC) for ETH/USD
ETH_USD_MIN, ETH_USD_MAX = 300.0, 20000.0   # a pool price outside this band is treated as unreadable: no send
ETH_REF_USD = 4000.0           # deliberately high reference price for the signed-cap check (ETH is about 1,800)
MAX_TX_USD = 0.90              # signed gas cap (maxFee x gasLimit + L1 allowance) at ETH_REF_USD stays under this
MAX_FEE_WEI = 100_000_000      # 0.1 gwei absolute ceiling for maxFeePerGas (base fee is 0.005 gwei)
MAX_GAS_LIMIT = 3_200_000      # fork: 1.52m used, estimate 1.89m; incumbents 1.3m-1.8m
SIM_GAS = 3_200_000
GAS_MARGIN_NUM, GAS_MARGIN_DEN = 12, 10    # gas limit = eth_estimateGas x 1.20 + GAS_EXTRA
GAS_EXTRA = 100_000            # the redeem and eight swaps cross more or fewer ticks than at estimate time
BASE_FEE_HEADROOM_PCT = 5      # maxFeePerGas = latest base fee x 1.05 + tip
# Base orders a block by priority fee; the incumbents pay 0.001-0.006 gwei over the base fee (README).
# The bot bids at most TIP_SHARE_PCT of the simulated gross, spread over the gas limit, within [MIN_TIP, MAX_TIP].
TIP_SHARE_PCT = 20
MIN_TIP_WEI = 100_000          # 0.0001 gwei; never 0 (the signer would replace 0 by maxFee / 10)
MAX_TIP_WEI = 50_000_000       # 0.05 gwei
L1_ALLOWANCE_WEI = 100_000_000_000   # OP Stack L1 data fee, not bounded by the signed fields: incumbents paid about 1e9 wei
ROUGH_GAS = 1_500_000          # only for the cheap pre-filter before an estimate is made
PROBE_MILLI = 20               # probe size in 0.001 WETH: small, so a small gap still shows (fork best size 0.04-0.05)
SIZES_MILLI = (10, 20, 40, 60, 80)  # flash-borrowed WETH, never the bot's own funds
POLL_INTERVAL = 30             # timer: one probe() eth_call (26 CU) every 30 s = 2,880 x 26 = 74,880 CU/day
BLOCK = 'latest'               # selftest.py replays check() at a past block by setting this
FEED_ENABLED = True            # LCAP/USDC pool Swap logs (about 150-200 a day, incumbents' takes included); Base had
                               # 9 of 16 feed filters in use on 2026-11-20. Basket-side price moves have no single
                               # event, so the 30 s timer stays the main trigger.
MIN_TRIGGER_GAP = 3            # seconds between two feed-triggered checks
SEND_COOLDOWN = 20             # per route
RELAY_CU_CAP = 93_000          # per UTC day; the feed's own CU is metered separately
CU_COST = {'eth_call': 26, 'eth_estimateGas': 20, 'eth_getLogs': 75, 'eth_getTransactionReceipt': 20,
           'eth_blockNumber': 10, 'eth_getBlockByNumber': 20, 'eth_getBalance': 20}
_id = 0


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


def calldata(route, amount_wei, min_profit):
    """ABI encoding of run(vault, weth, amount, Step[], minProfit); Step is a static 3-word tuple (checked against cast)."""
    steps = ROUTES[route]
    return (SEL_RUN + aword(VAULT) + aword(WETH) + word(amount_wei) + word(5 * 32) + word(min_profit)
            + word(len(steps)) + ''.join(word(k) + aword(t) + aword(i) for k, t, i in steps))


def probe_calldata(amount_wei):
    """ABI encoding of probe(vault, weth, amount, Step[][]) over every route (checked against cast in selftest.py)."""
    inner = [word(len(steps)) + ''.join(word(k) + aword(t) + aword(i) for k, t, i in steps)
             for steps in ROUTES.values()]
    offsets, pos = [], len(inner) * 32
    for x in inner:
        offsets.append(word(pos))
        pos += len(x) // 2
    return (SEL_PROBE + aword(VAULT) + aword(WETH) + word(amount_wei) + word(4 * 32)
            + word(len(inner)) + ''.join(offsets) + ''.join(inner))


def probe_all(ctx):
    """One eth_call: the executor tries every route at the probe size and reverts each trial. {route: gain or None}."""
    frm, to, ov = ctx
    params = [{'from': frm, 'to': to, 'data': probe_calldata(PROBE_MILLI * 10**15), 'gas': hex(PROBE_GAS)}, BLOCK]
    raw = rpc('eth_call', params + ([ov] if ov else []))[2:]
    n = int(raw[64:128], 16)
    if n != len(ROUTES):
        raise RuntimeError(f'probe returned {n} gains for {len(ROUTES)} routes')
    gains = [int(raw[128 + 64 * i: 192 + 64 * i], 16) for i in range(n)]
    return {route: (g or None) for route, g in zip(ROUTES, gains)}


def sim(data, ctx, gas=SIM_GAS):
    frm, to, ov = ctx
    params = [{'from': frm, 'to': to, 'data': data, 'gas': hex(gas)}, BLOCK] + ([ov] if ov else [])
    return int(rpc('eth_call', params)[2:66], 16)


def try_sim(data, ctx, gas=SIM_GAS):
    try:
        return sim(data, ctx, gas)
    except ReadBudgetExceeded:
        raise
    except RuntimeError:
        return None    # executor revert: the round trip does not pay


def estimate(data, ctx):
    frm, to, ov = ctx
    params = [{'from': frm, 'to': to, 'data': data}, BLOCK] + ([ov] if ov else [])
    return int(rpc('eth_estimateGas', params), 16)


def eth_usd():
    """USDC per WETH from slot0 of the Uniswap V3 WETH/USDC 0.01 pct pool (token0 WETH 18 dec, token1 USDC 6 dec)."""
    raw = rpc('eth_call', [{'to': WETH_USDC, 'data': SEL_SLOT0}, BLOCK])
    sqrt_p = int(raw[2:66], 16)
    price = sqrt_p * sqrt_p * 10**12 / 2**192
    if not ETH_USD_MIN < price < ETH_USD_MAX:
        raise RuntimeError(f'ETH/USD {price} outside the plausible band')
    return price


def wallet_bound(balance_wei, price, cap_wei):
    """The enforceable worst case of one send on an OP Stack chain is the wallet's native balance.
    Returns (ok, reason, balance_usd): ok only if the balance is worth less than WALLET_MAX_USD and covers the cap."""
    usd = balance_wei / 1e18 * price
    if usd >= WALLET_MAX_USD:
        return False, 'wallet_at_or_above_usd_bound', usd
    if balance_wei < cap_wei:
        return False, 'wallet_below_gas_cap', usd
    return True, None, usd


def winner_block(send_block, our_hash):
    """Block and tx of the last LCAP/USDC pool swap up to our block (ours if we won): the route swaps there."""
    logs = rpc('eth_getLogs', [{'address': LCAP_USDC, 'fromBlock': hex(max(0, send_block - 400)), 'toBlock': hex(send_block),
                                'topics': [SWAP_TOPIC]}])
    ours = [int(x['blockNumber'], 16) for x in logs if x['transactionHash'].lower() == our_hash.lower()]
    if ours:
        return min(ours), None
    if not logs:
        return None, None
    last = max(logs, key=lambda x: (int(x['blockNumber'], 16), int(x['logIndex'], 16)))
    return int(last['blockNumber'], 16), last['transactionHash']


def send_live(route, data, gas_limit, max_fee, tip, gross, min_profit, cap_wei, amount):
    import farmbot_signer
    reply = farmbot_signer.send(CHAIN, EXEC, data, 0, gas_limit, max_fee, max_priority_fee_per_gas=tip)
    h = None
    if isinstance(reply, dict):
        h = reply.get('txHash') or reply.get('tx_hash') or reply.get('hash')
    if not h:
        log('signer_reject', reply=reply, route=route, amount_wei=amount)   # final, never retried
        return
    log('send', hash=h, route=route, amount_wei=amount, gas_limit=gas_limit, max_fee=max_fee, priority=tip,
        gross_wei=gross, min_profit_wei=min_profit, gas_cap_wei=cap_wei, executor=EXEC)
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
        log('send_result', hash=h, route=route, result='unknown', gas_used=None, winner_block=None)
        return
    b = int(receipt['blockNumber'], 16)
    status = int(receipt['status'], 16)
    used = int(receipt['gasUsed'], 16)
    l1_fee = int(receipt.get('l1Fee') or '0x0', 16)
    cost = used * int(receipt['effectiveGasPrice'], 16) + l1_fee
    try:
        wb, wtx = winner_block(b, h)
    except Exception:
        wb, wtx = None, None
    log('send_result', hash=h, route=route, result='won' if status else 'lost', gas_used=used, gas_cost_wei=cost, l1_fee_wei=l1_fee,
        send_block=b, winner_block=wb, winner_tx=wtx, blocks_after_winner=(b - wb if wb is not None else None),
        expected_gross_wei=gross, net_wei=(gross - cost if status else -cost), amount_wei=amount)


def take(s, route, probe, trigger, ctx, now):
    """A route shows a gain at the probe size: sweep, cap, guard, then send or paper-log."""
    base_fee = int(rpc('eth_getBlockByNumber', [BLOCK, False])['baseFeePerGas'], 16)
    fee_floor = base_fee + base_fee * BASE_FEE_HEADROOM_PCT // 100 + MIN_TIP_WEI
    if probe <= ROUGH_GAS * fee_floor * 8 // 10:
        log('check', trigger=trigger, route=route, probe_gain_wei=probe, base_fee=base_fee, reason='gain_below_gas')
        return False
    rows = {PROBE_MILLI: probe}
    for size in SIZES_MILLI:
        if size != PROBE_MILLI:
            rows[size] = try_sim(calldata(route, size * 10**15, 1), ctx)
    size, gross = max(((k, v) for k, v in rows.items() if v), key=lambda x: x[1])
    amount = size * 10**15
    try:
        est = estimate(calldata(route, amount, 1), ctx)
    except RuntimeError as e:
        log('opportunity_skip', route=route, reason='estimate_revert', error=str(e)[:160], amount_wei=amount, gross_wei=gross)
        return False
    gas_limit = est * GAS_MARGIN_NUM // GAS_MARGIN_DEN + GAS_EXTRA
    tip = max(MIN_TIP_WEI, min(MAX_TIP_WEI, gross * TIP_SHARE_PCT // 100 // gas_limit))   # bid: at most 20 pct of gross
    max_fee = base_fee + base_fee * BASE_FEE_HEADROOM_PCT // 100 + tip
    cap_wei = gas_limit * max_fee + L1_ALLOWANCE_WEI   # expected ceiling of one send; the L1 allowance is an estimate, the bound is wallet_bound()
    cap_usd = cap_wei / 1e18 * ETH_REF_USD
    min_profit = cap_wei + 1                     # a win always pays more than the signed gas cap
    log('opportunity', trigger=trigger, route=route, sweep=rows, amount_wei=amount, gross_wei=gross, base_fee=base_fee,
        gas_estimate=est, gas_limit=gas_limit, max_fee=max_fee, priority=tip, gas_cap_wei=cap_wei,
        gas_cap_usd_at_ref=cap_usd, min_profit_wei=min_profit)
    if max_fee > MAX_FEE_WEI or gas_limit > MAX_GAS_LIMIT or cap_usd >= MAX_TX_USD:
        log('opportunity_skip', route=route, reason='fee_gas_or_usd_cap', max_fee=max_fee, gas_limit=gas_limit,
            gas_cap_usd_at_ref=cap_usd)
        return False
    if gross <= cap_wei:
        log('opportunity_skip', route=route, reason='gross_below_gas_cap', gross_wei=gross, gas_cap_wei=cap_wei)
        return False
    if s.setdefault('cooldown', {}).get(route, 0) > now:
        log('opportunity_skip', route=route, reason='cooldown')
        return False
    data = calldata(route, amount, min_profit)
    checked = try_sim(data, ctx, gas_limit)      # the exact guarded call at the signed gas limit
    if not checked:
        log('simulate_revert', route=route, amount_wei=amount, min_profit_wei=min_profit, gas_limit=gas_limit)
        return False
    # OP Stack loss bound: one send can cost at most the wallet's native balance, which must be worth under 1 USD.
    try:
        price = eth_usd()
    except RuntimeError as e:
        log('opportunity_skip', route=route, reason='eth_usd_unreadable', error=str(e)[:160])
        return False
    s['cooldown'][route] = now + SEND_COOLDOWN
    if MODE == 'live':
        balance = int(rpc('eth_getBalance', [ctx[0], 'latest']), 16)
        ok, reason, usd = wallet_bound(balance, price, cap_wei)
        if not ok:
            log('opportunity_skip', route=route, reason=reason, wallet_wei=balance, wallet_usd=usd, eth_usd=price,
                wallet_max_usd=WALLET_MAX_USD, gas_cap_wei=cap_wei)
            return False
        log('wallet_bound', route=route, wallet_wei=balance, wallet_usd=usd, eth_usd=price, wallet_max_usd=WALLET_MAX_USD)
        send_live(route, data, gas_limit, max_fee, tip, checked, min_profit, cap_wei, amount)
    else:
        log('paper_sim', result='success', route=route, amount_wei=amount, gross_wei=checked, min_profit_wei=min_profit,
            gas_limit=gas_limit, max_fee=max_fee, priority=tip, gas_cap_wei=cap_wei, net_wei_at_cap=checked - cap_wei,
            eth_usd=price, gas_cap_usd=cap_wei / 1e18 * price, wallet_max_usd=WALLET_MAX_USD)
    return True


def check(s, trigger):
    """One look at the chain: probe every route, act on those that show a gain."""
    now = time.time()
    s['last_check'] = now
    ctx = exec_ctx()
    probes = probe_all(ctx)
    live ={r: g for r, g in probes.items() if g}
    if not live:
        log('check', trigger=trigger, probes=probes, reason='nothing_to_take')
        return
    for route, gain in sorted(live.items(), key=lambda x: -x[1]):
        if take(s, route, gain, trigger, ctx, now):
            break    # one send per look


def load_state():
    try:
        return json.loads(STATE.read_text())
    except Exception:
        return {'feed_cursor': None, 'last_check': 0, 'cooldown': {}}


def save_state(s):
    tmp = STATE.with_suffix('.tmp')
    tmp.write_text(json.dumps(s, separators=(',', ':')))
    tmp.replace(STATE)


def feed_wait(cursor, timeout):
    q = {'address': LCAP_USDC, 'topic0': SWAP_TOPIC, 'timeout': str(timeout)}
    if cursor:
        q['after'] = cursor
    with urllib.request.urlopen(FEED + '?' + urllib.parse.urlencode(q), timeout=timeout + 10) as r:
        return json.load(r)


def main():
    s = load_state()
    log('start', mode=MODE, executor=(EXEC if MODE == 'live' else PAPER_EXEC), feed=FEED_ENABLED, feed_pool=LCAP_USDC,
        routes=list(ROUTES), poll_seconds=POLL_INTERVAL)
    while True:
        try:
            wait = POLL_INTERVAL - (time.time() - s.get('last_check', 0))
            if wait <= 0:
                check(s, 'timer')
                save_state(s)
                continue
            if not FEED_ENABLED:
                time.sleep(wait)
                continue
            # the feed long-poll is the sleep; an LCAP/USDC pool swap or a gap triggers a check at once
            result = feed_wait(s.get('feed_cursor'), max(1, min(55, int(wait) + 1)))
            s['feed_cursor'] = result.get('cursor', s.get('feed_cursor'))
            if result.get('gap') or result.get('logs'):
                if time.time() - s.get('last_check', 0) >= MIN_TRIGGER_GAP:
                    check(s, 'gap' if result.get('gap') else 'pool_swap')
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
            log('feed_error', error=str(e)[:180])   # 429/503/timeout: the timer keeps re-reading state
            time.sleep(min(30, max(1, POLL_INTERVAL - (time.time() - s.get('last_check', 0)))))
        except ReadBudgetExceeded as e:
            log('read_budget', error=str(e))
            time.sleep(600)
        except Exception as e:
            log('loop_error', error=str(e)[:250])
            time.sleep(5)
        save_state(s)


if __name__ == '__main__':
    main()
