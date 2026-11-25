"""trial-rtoken-nav-base: Reserve yield DTF (RToken) bsdETH redeem round trip on Base, one atomic executor call.

bsdETH ("Based ETH") is redeemed for its basket (wsuperOETHb, cbETH, wstETH) by anyone with RToken.redeem(uint256).
When bsdETH is cheap in its Aerodrome vAMM-WETH/bsdETH pool relative to the basket, the round trip
WETH -> bsdETH -> redeem -> unwrap wsuperOETHb -> sell superOETHb, cbETH, wstETH for WETH pays. At least six executors
take it, 4-180 times a day, for 0.04-0.14 USD each (README). The bot calls the executor's probe() (one eth_call that
tries every size) on a timer and on every Swap of the bsdETH pool (feed) and, when the simulated WETH gain exceeds the
signed gas cap, sends it (BOT_MODE=live) or logs a paper simulation (BOT_MODE=paper). The executor reverts unless its
WETH balance grows by minProfit after the flash loan is repaid, so a lost attempt costs gas only.
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

# Addresses: read from an incumbent's take (scratch/r2f4e/trace-0xfa0c30ec.json), the RToken and its BasketHandler from
# Reserve's own deployment page (scratch/reserve-research/8453-bsdETH.md), checked with symbol() / token0() / token1()
# / asset() getters (scratch/r2f4e/ident.py) and BasketHandler.quote() (scratch/r2f4e/rtoken.py), see README.
VAULT = '0xba12222222228d8ba445958a75a0704d566bf2c8'        # Balancer V2 Vault, flash loan fee 0
WETH = '0x4200000000000000000000000000000000000006'
BSDETH = '0xcb327b99ff831bf8223cced12b1338ff3aa322ff'       # Reserve RToken "Based ETH"
WSOETH = '0x7fcd174e80f264448ebee8c88a7c4476aaf58ea6'       # wsuperOETHb, ERC-4626 over superOETHb
SOETH = '0xdbfefd2e8460a6ee4955a68582f85708baea60a3'        # superOETHb
CBETH = '0x2ae3f1ec7f1f5012cfeab0185bfc7aa3cf0dec22'
WSTETH = '0xc1cba3fcea344f92d9239c08c0568f6f2f0ee452'
P_BSD = '0x6b87b8663ee63191887f18225f79d9eeb2de0d34'        # Aerodrome vAMM-WETH/bsdETH (Solidly-style V2 pool)
P_SOETH = '0x6446021f4e396da3df4235c62537431372195d38'      # Slipstream WETH/superOETHb
P_CBETH = '0x47ca96ea59c13f72745928887f84c9f52c3d7348'      # Slipstream cbETH/WETH
P_WSTETH = '0x20e068d76f9e90b90604500b84c7e19dcb923e7e'     # UniV3-style WETH/wstETH
WETH_USDC = '0xb4cb800910b228ed3d0834cf79d697127bbb00e5'    # Uniswap V3 WETH/USDC 0.01 pct, read only (ETH/USD)
Z = '0x0000000000000000000000000000000000000000'
# Step = (kind, target, tokenIn): 0 UniV3-style pool swap, 1 Solidly-style V2 pool swap, 2 RToken redeem,
# 3 ERC-4626 redeem. Each step spends the executor's whole balance of its input token (kinds 2 and 3: of the share).
ROUTE_NAME = 'bsdeth_redeem'
ROUTE = [(1, P_BSD, WETH), (2, BSDETH, Z), (3, WSOETH, Z), (0, P_SOETH, SOETH), (0, P_CBETH, CBETH), (0, P_WSTETH, WSTETH)]
SWAP_TOPIC = '0xb3e2773606abfd36b5bd91394b3a54d1398336c65005baf7bf7a05efeffaf75b'  # cast keccak Swap(address,address,uint256,uint256,uint256,uint256)
SEL_RUN = '0xe1fac79a'    # cast sig run(address,address,uint256,(uint8,address,address)[],uint256)
SEL_PROBE = '0xa309ec12'  # cast sig probe(address,address,uint256[],(uint8,address,address)[])
PROBE_GAS = 30_000_000    # eth_call only: one reverted trial of about 1.3m gas per size

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
# while balance x ETH/USD is WALLET_MAX_USD or more (same guard as the reviewed trial-folio-nav-base).
WALLET_MAX_USD = 0.95          # live: no send while the bot wallet's native balance is worth this much or more
SEL_SLOT0 = '0x3850c7bd'       # cast sig slot0(); read on WETH_USDC (token0 = WETH, token1 = USDC) for ETH/USD
ETH_USD_MIN, ETH_USD_MAX = 300.0, 20000.0   # a pool price outside this band is treated as unreadable: no send
ETH_REF_USD = 4000.0           # deliberately high reference price for the signed-cap check (ETH is about 1,750)
MAX_TX_USD = 0.90              # signed gas cap (maxFee x gasLimit + L1 allowance) at ETH_REF_USD stays under this
MAX_FEE_WEI = 100_000_000      # 0.1 gwei absolute ceiling for maxFeePerGas (base fee is about 0.005 gwei)
MAX_GAS_LIMIT = 3_000_000      # fork: 1.27m used, estimate 1.51m; incumbents 1.17m-1.65m
GAS_MARGIN_NUM, GAS_MARGIN_DEN = 12, 10    # gas limit = eth_estimateGas x 1.20 + GAS_EXTRA
GAS_EXTRA = 100_000            # the redeem refreshes every basket asset; the swaps cross more or fewer ticks
BASE_FEE_HEADROOM_PCT = 5      # maxFeePerGas = latest base fee x 1.05 + tip
# Base orders a block by priority fee; the incumbents pay 0.0005-0.006 gwei over the base fee (README).
# The bot bids at most TIP_SHARE_PCT of the simulated gross, spread over the gas limit, within [MIN_TIP, MAX_TIP].
TIP_SHARE_PCT = 20
MIN_TIP_WEI = 100_000          # 0.0001 gwei; never 0 (the signer would replace 0 by maxFee / 10)
MAX_TIP_WEI = 50_000_000       # 0.05 gwei
L1_ALLOWANCE_WEI = 100_000_000_000   # OP Stack L1 data fee, not bounded by the signed fields: incumbents paid about 1e9 wei
SIZES_MILLI = (10, 20, 30, 50, 70, 100)   # flash-borrowed WETH in 0.001, never the bot's own funds (fork best 0.05)
POLL_INTERVAL = 60             # timer: one probe() eth_call (26 CU) every 60 s = 1,440 x 26 = 37,440 CU/day
BLOCK = 'latest'               # selftest.py replays check() at a past block by setting this
FEED_ENABLED = True            # bsdETH pool Swap logs (about 20-200 a day, incumbents' takes included); Base had
                               # 10 of 16 feed filters in use on 2026-11-20. Basket-side price moves have no single
                               # event, so the 60 s timer stays as the second trigger.
MIN_TRIGGER_GAP = 3            # seconds between two feed-triggered checks
SEND_COOLDOWN = 20
RELAY_CU_CAP = 90_000          # per UTC day; the feed's own CU is metered separately
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


def steps_words():
    return word(len(ROUTE)) + ''.join(word(k) + aword(t) + aword(i) for k, t, i in ROUTE)


def calldata(amount_wei, min_profit):
    """ABI encoding of run(vault, weth, amount, Step[], minProfit); Step is a static 3-word tuple (checked against cast)."""
    return SEL_RUN + aword(VAULT) + aword(WETH) + word(amount_wei) + word(5 * 32) + word(min_profit) + steps_words()


def probe_calldata(amounts_wei):
    """ABI encoding of probe(vault, weth, uint256[] amounts, Step[] steps) (checked against cast in selftest.py)."""
    amounts = word(len(amounts_wei)) + ''.join(word(a) for a in amounts_wei)
    return (SEL_PROBE + aword(VAULT) + aword(WETH) + word(4 * 32) + word(4 * 32 + len(amounts) // 2)
            + amounts + steps_words())


def probe_sizes(ctx):
    """One eth_call: the executor tries the route at every size and reverts each trial. {size in 0.001 WETH: gain or None}."""
    frm, to, ov = ctx
    params = [{'from': frm, 'to': to, 'data': probe_calldata([s * 10**15 for s in SIZES_MILLI]), 'gas': hex(PROBE_GAS)}, BLOCK]
    raw = rpc('eth_call', params + ([ov] if ov else []))[2:]
    n = int(raw[64:128], 16)
    if n != len(SIZES_MILLI):
        raise RuntimeError(f'probe returned {n} gains for {len(SIZES_MILLI)} sizes')
    gains = [int(raw[128 + 64 * i: 192 + 64 * i], 16) for i in range(n)]
    return {s: (g or None) for s, g in zip(SIZES_MILLI, gains)}


def sim(data, ctx, gas):
    frm, to, ov = ctx
    params = [{'from': frm, 'to': to, 'data': data, 'gas': hex(gas)}, BLOCK] + ([ov] if ov else [])
    return int(rpc('eth_call', params)[2:66], 16)


def try_sim(data, ctx, gas):
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
    """Block and tx of the last bsdETH pool swap up to our block (ours if we won): the route swaps there."""
    logs = rpc('eth_getLogs', [{'address': P_BSD, 'fromBlock': hex(max(0, send_block - 400)), 'toBlock': hex(send_block),
                                'topics': [SWAP_TOPIC]}])
    ours = [int(x['blockNumber'], 16) for x in logs if x['transactionHash'].lower() == our_hash.lower()]
    if ours:
        return min(ours), None
    if not logs:
        return None, None
    last = max(logs, key=lambda x: (int(x['blockNumber'], 16), int(x['logIndex'], 16)))
    return int(last['blockNumber'], 16), last['transactionHash']


def send_live(data, gas_limit, max_fee, tip, gross, min_profit, cap_wei, amount):
    import farmbot_signer
    reply = farmbot_signer.send(CHAIN, EXEC, data, 0, gas_limit, max_fee, max_priority_fee_per_gas=tip)
    h = None
    if isinstance(reply, dict):
        h = reply.get('txHash') or reply.get('tx_hash') or reply.get('hash')
    if not h:
        log('signer_reject', reply=reply, route=ROUTE_NAME, amount_wei=amount)   # final, never retried
        return
    log('send', hash=h, route=ROUTE_NAME, amount_wei=amount, gas_limit=gas_limit, max_fee=max_fee, priority=tip,
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
        log('send_result', hash=h, route=ROUTE_NAME, result='unknown', gas_used=None, winner_block=None)
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
    log('send_result', hash=h, route=ROUTE_NAME, result='won' if status else 'lost', gas_used=used, gas_cost_wei=cost,
        l1_fee_wei=l1_fee, send_block=b, winner_block=wb, winner_tx=wtx,
        blocks_after_winner=(b - wb if wb is not None else None), expected_gross_wei=gross,
        net_wei=(gross - cost if status else -cost), amount_wei=amount)


def take(s, rows, trigger, ctx, now):
    """The route shows a gain at some size: cap, guard, then send or paper-log."""
    size, gross = max(((k, v) for k, v in rows.items() if v), key=lambda x: x[1])
    amount = size * 10**15
    base_fee = int(rpc('eth_getBlockByNumber', [BLOCK, False])['baseFeePerGas'], 16)
    try:
        est = estimate(calldata(amount, 1), ctx)
    except RuntimeError as e:
        log('opportunity_skip', route=ROUTE_NAME, reason='estimate_revert', error=str(e)[:160], amount_wei=amount, gross_wei=gross)
        return False
    gas_limit = est * GAS_MARGIN_NUM // GAS_MARGIN_DEN + GAS_EXTRA
    tip = max(MIN_TIP_WEI, min(MAX_TIP_WEI, gross * TIP_SHARE_PCT // 100 // gas_limit))   # bid: at most 20 pct of gross
    max_fee = base_fee + base_fee * BASE_FEE_HEADROOM_PCT // 100 + tip
    cap_wei = gas_limit * max_fee + L1_ALLOWANCE_WEI   # expected ceiling of one send; the L1 allowance is an estimate, the bound is wallet_bound()
    cap_usd = cap_wei / 1e18 * ETH_REF_USD
    min_profit = cap_wei + 1                     # a win always pays more than the signed gas cap
    log('opportunity', trigger=trigger, route=ROUTE_NAME, sweep=rows, amount_wei=amount, gross_wei=gross, base_fee=base_fee,
        gas_estimate=est, gas_limit=gas_limit, max_fee=max_fee, priority=tip, gas_cap_wei=cap_wei,
        gas_cap_usd_at_ref=cap_usd, min_profit_wei=min_profit)
    if max_fee > MAX_FEE_WEI or gas_limit > MAX_GAS_LIMIT or cap_usd >= MAX_TX_USD:
        log('opportunity_skip', route=ROUTE_NAME, reason='fee_gas_or_usd_cap', max_fee=max_fee, gas_limit=gas_limit,
            gas_cap_usd_at_ref=cap_usd)
        return False
    if gross <= cap_wei:
        log('opportunity_skip', route=ROUTE_NAME, reason='gross_below_gas_cap', gross_wei=gross, gas_cap_wei=cap_wei)
        return False
    if s.get('cooldown_until', 0) > now:
        log('opportunity_skip', route=ROUTE_NAME, reason='cooldown')
        return False
    data = calldata(amount, min_profit)
    checked = try_sim(data, ctx, gas_limit)      # the exact guarded call at the signed gas limit
    if not checked:
        log('simulate_revert', route=ROUTE_NAME, amount_wei=amount, min_profit_wei=min_profit, gas_limit=gas_limit)
        return False
    # OP Stack loss bound: one send can cost at most the wallet's native balance, which must be worth under 1 USD.
    try:
        price = eth_usd()
    except RuntimeError as e:
        log('opportunity_skip', route=ROUTE_NAME, reason='eth_usd_unreadable', error=str(e)[:160])
        return False
    s['cooldown_until'] = now + SEND_COOLDOWN
    if MODE == 'live':
        balance = int(rpc('eth_getBalance', [ctx[0], 'latest']), 16)
        ok, reason, usd = wallet_bound(balance, price, cap_wei)
        if not ok:
            log('opportunity_skip', route=ROUTE_NAME, reason=reason, wallet_wei=balance, wallet_usd=usd, eth_usd=price,
                wallet_max_usd=WALLET_MAX_USD, gas_cap_wei=cap_wei)
            return False
        log('wallet_bound', route=ROUTE_NAME, wallet_wei=balance, wallet_usd=usd, eth_usd=price, wallet_max_usd=WALLET_MAX_USD)
        send_live(data, gas_limit, max_fee, tip, checked, min_profit, cap_wei, amount)
    else:
        log('paper_sim', result='success', route=ROUTE_NAME, amount_wei=amount, gross_wei=checked, min_profit_wei=min_profit,
            gas_limit=gas_limit, max_fee=max_fee, priority=tip, gas_cap_wei=cap_wei, net_wei_at_cap=checked - cap_wei,
            eth_usd=price, gas_cap_usd=cap_wei / 1e18 * price, wallet_max_usd=WALLET_MAX_USD)
    return True


# Read saver, not a loss guard: a gain this small cannot pass the gas-cap test in take() (1.5m gas x 0.0035 gwei), so
# the three extra reads of take() are skipped while a small gap stands for hours (kept below take() so that the line
# numbers the manifest cites do not move).
MIN_GROSS_WEI = 5_000_000_000_000


def check(s, trigger):
    """One look at the chain: probe every size, act when one shows a gain."""
    now = time.time()
    s['last_check'] = now
    ctx = exec_ctx()
    rows = probe_sizes(ctx)
    best = max((v for v in rows.values() if v), default=0)
    if not best:
        log('check', trigger=trigger, reason='nothing_to_take')
        return
    if best < MIN_GROSS_WEI:
        log('check', trigger=trigger, reason='gain_below_floor', best_gain_wei=best, floor_wei=MIN_GROSS_WEI)
        return
    take(s, rows, trigger, ctx, now)


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
    q = {'address': P_BSD, 'topic0': SWAP_TOPIC, 'timeout': str(timeout)}
    if cursor:
        q['after'] = cursor
    with urllib.request.urlopen(FEED + '?' + urllib.parse.urlencode(q), timeout=timeout + 10) as r:
        return json.load(r)


def main():
    s = load_state()
    log('start', mode=MODE, executor=(EXEC if MODE == 'live' else PAPER_EXEC), feed=FEED_ENABLED, feed_pool=P_BSD,
        route=ROUTE_NAME, poll_seconds=POLL_INTERVAL)
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
            # the feed long-poll is the sleep; a bsdETH pool swap or a gap triggers a check at once
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
