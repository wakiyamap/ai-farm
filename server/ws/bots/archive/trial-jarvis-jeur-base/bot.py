"""trial-jarvis-jeur-base: Jarvis jEUR / EURC fixed-rate wrapper round trips on Base, one atomic executor call.

jEUR (Jarvis Synthetic Euro) is minted from EURC and burnt back to EURC 1:1 by anyone through the
SynthereumFixedRateLendingWrapper (wrap / unwrap). When the jEUR/USDC pool drifts from the EURC/USDC pool, a round trip
USDC -> jEUR -> unwrap -> EURC -> USDC pays (and the mirror with wrap when jEUR is dear). One operator (executor
0x1470dab4, EOA 0x62e88a85) takes about 47 of these a day for 0.01-0.14 USDC each (README). The bot waits on the farm feed for a
Swap log of the jEUR/USDC pool (about 72 a day: every jEUR trade and every round trip emits one), re-reads state on a
feed gap / 429 / 503 / error and on a 5 min safety poll, and after a look that leaves a gain standing below its send
line looks again 10 s and 40 s later. Each look asks the executor's probe() for the gain of both directions at six
sizes in one eth_call; when the best gain is above the signed gas cap it sends take() (BOT_MODE=live) or logs a paper
simulation (BOT_MODE=paper). The EURC/USDC pool's Swap (about 4,100 a day) is a busy event and is not subscribed. The executor reverts
unless its USDC balance grows by minProfit after the Morpho flash loan is repaid, so a lost attempt costs gas only.
"""
import datetime
import json
import os
import sys
import time
from pathlib import Path
import urllib.error
import urllib.parse
import urllib.request

sys.path.append('/opt/farm/lib')   # farmbot_signer lives here; the live service does not add it

HERE = Path(__file__).resolve().parent
MODE = os.environ.get('BOT_MODE', 'paper')
LANE = os.environ.get('RPC_LANE', 'paper')
RELAY = os.environ['RPC_RELAY_URL'].rstrip('/')
CHAIN = 'base'
FEED = os.environ.get('FEED_URL', 'http://127.0.0.1:8546').rstrip('/')   # farm-feed (wiki infra/feed.md)

# Addresses: read from the incumbent's take 0xd3024e21... (scratch/flash2-cb04/trace-0xd3024e21.json) and checked with
# getters (collateralToken(), syntheticToken(), conversionRate(), token0()/token1(), fee(); scratch/flash2-cb04/probe.py).
MORPHO = '0xbbbbbbbbbb9cc5e90e3b3af64bdaf62c37eeffcb'       # Morpho Blue: flashLoan, fee 0
USDC = '0x833589fcd6edb6e08f4c7c32d4f71b54bda02913'
JEUR = '0x4154550f4db74dc38d1fe98e1f3f28ed6dad627d'         # Jarvis Synthetic Euro, 18 decimals
EURC = '0x60a3e35cc302bfa44cb288bc5a4f316fdb1adb42'         # 6 decimals
WRAPPER = '0x41b0667ea45a5401d95f9a5d281287630704b798'      # SynthereumFixedRateLendingWrapper, rate 1e18
POOL_JEUR = '0x9a8f6327dd5a9fc87ee9be06cf7fd2e069efb62b'    # jEUR/USDC, fee 0.0486 pct (UniV3-style swap + callback)
POOL_EURC = '0x6eaec4f69c92bd16a4b018ceb6fe7a446a113598'    # EURC/USDC, fee 0.007 pct, same factory
WETH_USDC = '0xb4cb800910b228ed3d0834cf79d697127bbb00e5'    # Uniswap V3 WETH/USDC 0.01 pct: ETH/USD for the gas cap
SYNTH_UNIT = 10**12                                         # unwrap takes multiples of 1e12 jEUR wei (EURC has 6 decimals)
ROUTES = {'unwrap': True, 'wrap': False}                    # unwrapFirst flag of the executor's Route
SIZES_USDC = (300, 700, 1200, 2000, 3000, 5000)             # flash-borrowed USDC, never the bot's own funds
UNWRAP_TOPIC = '0x844bdb9a38d1fd821344dfafdefc02959dbbcddd8e8f158cdebb56b561cb6702'   # cast keccak Unwrap(address,address,uint256,uint256)
WRAP_TOPIC = '0x764bd851d2423ff95fbc9b4db718c64299b808c0948fa9eec41c3b30001aea5e'     # cast keccak Wrap(address,address,uint256,uint256)
SWAP_TOPIC = '0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67'     # cast keccak Swap(address,address,int256,int256,uint160,uint128,int24)
SEL_TAKE = '0x84c3f02d'    # cast sig take((address,address,address,address,address,address,address,uint256,bool),uint256,uint256)
SEL_PROBE = '0xd7f6aeef'   # cast sig probe((address,address,address,address,address,address,address,uint256,bool)[],uint256[])
SEL_SLOT0 = '0x3850c7bd'   # cast sig slot0()
PROBE_GAS = 30_000_000     # eth_call only: twelve reverted trials of about 1.1m gas each

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
# while balance x ETH/USD is WALLET_MAX_USD or more.
WALLET_MAX_USD = 0.95          # live: no send while the bot wallet's native balance is worth this much or more
ETH_USD_MIN, ETH_USD_MAX = 300.0, 20000.0   # a pool price outside this band is treated as unreadable: no send
ETH_REF_USD = 4000.0           # deliberately high reference price for the absolute cap check (ETH is about 1,800)
MAX_TX_USD = 0.90              # signed gas cap (maxFee x gasLimit + L1 allowance) at ETH_REF_USD stays under this
MAX_FEE_WEI = 100_000_000      # 0.1 gwei absolute ceiling for maxFeePerGas (base fee is 0.005 gwei)
MAX_GAS_LIMIT = 2_500_000      # fork: about 0.95m-1.05m used
GAS_MARGIN_NUM, GAS_MARGIN_DEN = 12, 10    # gas limit = eth_estimateGas x 1.20 + GAS_EXTRA
GAS_EXTRA = 200_000            # the wrapper withdraws from a Morpho vault whose path can change between blocks
BASE_FEE_HEADROOM_PCT = 5      # maxFeePerGas = latest base fee x 1.05 + tip
# The incumbent bids 0.002-0.03 gwei. The bot bids at most TIP_SHARE_PCT of the simulated gross, within [MIN, MAX].
TIP_SHARE_PCT = 20
MIN_TIP_WEI = 100_000          # 0.0001 gwei; never 0 (the signer would replace 0 by maxFee / 10)
MAX_TIP_WEI = 50_000_000       # 0.05 gwei
L1_ALLOWANCE_WEI = 100_000_000_000   # OP Stack L1 data fee estimate (not a bound; the bound is the wallet balance)
GROSS_MARGIN_PCT = 10          # the gain is USDC and the gas is ETH: gross must exceed the cap by this much
MIN_GROSS_UNITS = 15_000       # 0.015 USDC: under any signed cap seen (0.019 USD at the minimum tip); no further reads
# Trigger: feed /logs filter = address POOL_JEUR, topic0 SWAP_TOPIC (measured 18 Swap logs in 6 h = about 72 a day).
SAFETY_POLL = 300              # one probe() when nothing was looked at for this long (feed rule: 5-10 min) = 288 x 26 CU
FEED_TIMEOUT = 55              # long-poll seconds
FEED_DOWN_POLL = 60            # while the feed answers 429 / 503 / errors: one state re-read at most this often
FOLLOW_UPS = (10, 40)          # seconds after a look that left a gain standing below the send line; a follow-up arms nothing
SEND_COOLDOWN = 20
RELAY_CU_CAP = 60_000          # per UTC day
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


def route_words(route):
    """The executor's Route struct: nine static words (checked against cast in selftest.py)."""
    return (aword(MORPHO) + aword(USDC) + aword(JEUR) + aword(EURC) + aword(WRAPPER) + aword(POOL_JEUR) + aword(POOL_EURC)
            + word(SYNTH_UNIT) + word(1 if ROUTES[route] else 0))


def calldata(route, amount, min_profit):
    """take(Route, amount, minProfit): all static, eleven words."""
    return SEL_TAKE + route_words(route) + word(amount) + word(min_profit)


def probe_calldata():
    """probe(Route[], uint256[]) over both directions and every size."""
    routes = ''.join(route_words(r) for r in ROUTES)
    amounts = ''.join(word(s * 10**6) for s in SIZES_USDC)
    off_amounts = 0x40 + 32 + len(routes) // 2
    return SEL_PROBE + word(0x40) + word(off_amounts) + word(len(ROUTES)) + routes + word(len(SIZES_USDC)) + amounts


def probe_all(ctx):
    """One eth_call: every (direction, size) tried and reverted. {(route, usdc): gain in USDC units} for gains > 0."""
    frm, to, ov = ctx
    params = [{'from': frm, 'to': to, 'data': probe_calldata(), 'gas': hex(PROBE_GAS)}, 'latest']
    raw = rpc('eth_call', params + ([ov] if ov else []))[2:]
    n = int(raw[64:128], 16)
    if n != len(ROUTES) * len(SIZES_USDC):
        raise RuntimeError(f'probe returned {n} gains')
    gains = [int(raw[128 + 64 * i: 192 + 64 * i], 16) for i in range(n)]
    keys = [(r, s) for r in ROUTES for s in SIZES_USDC]
    return {k: g for k, g in zip(keys, gains) if g}


def sim(data, ctx, gas):
    frm, to, ov = ctx
    params = [{'from': frm, 'to': to, 'data': data, 'gas': hex(gas)}, 'latest'] + ([ov] if ov else [])
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
    params = [{'from': frm, 'to': to, 'data': data}, 'latest'] + ([ov] if ov else [])
    return int(rpc('eth_estimateGas', params), 16)


def eth_usd():
    """USDC per WETH from slot0 of the Uniswap V3 WETH/USDC 0.01 pct pool (token0 WETH 18 dec, token1 USDC 6 dec)."""
    raw = rpc('eth_call', [{'to': WETH_USDC, 'data': SEL_SLOT0}, 'latest'])
    sqrt_p = int(raw[2:66], 16)
    price = sqrt_p * sqrt_p * 10**12 / 2**192
    if not ETH_USD_MIN < price < ETH_USD_MAX:
        raise RuntimeError(f'ETH/USD {price} outside the plausible band')
    return price


def wei_to_usdc_units(wei, price):
    return int(wei * price / 10**12) + 1     # wei -> USDC 6-decimals units at `price` USD per ETH, rounded up


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
    """Block and tx of the last Wrap / Unwrap at the wrapper up to our block (ours if we won): every take emits one."""
    logs = rpc('eth_getLogs', [{'address': WRAPPER, 'fromBlock': hex(max(0, send_block - 400)), 'toBlock': hex(send_block),
                                'topics': [[UNWRAP_TOPIC, WRAP_TOPIC]]}])
    ours = [int(x['blockNumber'], 16) for x in logs if x['transactionHash'].lower() == our_hash.lower()]
    if ours:
        return min(ours), None
    if not logs:
        return None, None
    last = max(logs, key=lambda x: (int(x['blockNumber'], 16), int(x['logIndex'], 16)))
    return int(last['blockNumber'], 16), last['transactionHash']


def send_live(route, data, gas_limit, max_fee, tip, gross, min_profit, cap_wei, amount, price):
    import farmbot_signer
    reply = farmbot_signer.send(CHAIN, EXEC, data, 0, gas_limit, max_fee, max_priority_fee_per_gas=tip)
    h = None
    if isinstance(reply, dict):
        h = reply.get('txHash') or reply.get('tx_hash') or reply.get('hash')
    if not h:
        log('signer_reject', reply=reply, route=route, amount_usdc_units=amount)   # final, never retried
        return
    log('send', hash=h, route=route, amount_usdc_units=amount, gas_limit=gas_limit, max_fee=max_fee, priority=tip,
        gross_usdc_units=gross, min_profit_usdc_units=min_profit, gas_cap_wei=cap_wei, executor=EXEC)
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
    cost_usd = cost / 1e18 * price
    try:
        wb, wtx = winner_block(b, h)
    except Exception:
        wb, wtx = None, None
    log('send_result', hash=h, route=route, result='won' if status else 'lost', gas_used=used, gas_cost_wei=cost,
        gas_cost_usd=cost_usd, l1_fee_wei=l1_fee, send_block=b, winner_block=wb, winner_tx=wtx,
        blocks_after_winner=(b - wb if wb is not None else None), expected_gross_usdc_units=gross,
        net_usd=((gross / 1e6 - cost_usd) if status else -cost_usd), amount_usdc_units=amount)


def take(s, route, size, gross, trigger, ctx, now, table):
    """The probe shows a gain: cap, guard, then send or paper-log. gross is in USDC units (6 decimals)."""
    amount = size * 10**6
    base_fee = int(rpc('eth_getBlockByNumber', ['latest', False])['baseFeePerGas'], 16)
    try:
        price = eth_usd()
    except RuntimeError as e:
        log('opportunity_skip', route=route, reason='eth_usd_unreadable', error=str(e)[:160])
        return False
    try:
        est = estimate(calldata(route, amount, 1), ctx)
    except RuntimeError as e:
        log('opportunity_skip', route=route, reason='estimate_revert', error=str(e)[:160], amount_usdc_units=amount,
            gross_usdc_units=gross)
        return False
    gas_limit = est * GAS_MARGIN_NUM // GAS_MARGIN_DEN + GAS_EXTRA
    gross_wei = int(gross * 10**12 / price)
    fee_floor = base_fee + base_fee * BASE_FEE_HEADROOM_PCT // 100
    # bid: at most 20 pct of gross, and never so much that the signed cap (with its margin) would exceed the gross.
    # Small gaps stand for a minute or more below the incumbent's threshold (README): those go out at the minimum tip.
    afford = (gross_wei * 100 // (100 + GROSS_MARGIN_PCT + 1) - L1_ALLOWANCE_WEI) // gas_limit - fee_floor
    tip = max(MIN_TIP_WEI, min(MAX_TIP_WEI, gross_wei * TIP_SHARE_PCT // 100 // gas_limit, afford))
    max_fee = fee_floor + tip
    cap_wei = gas_limit * max_fee + L1_ALLOWANCE_WEI   # expected ceiling of one send; the bound is wallet_bound()
    cap_units = wei_to_usdc_units(cap_wei, price)
    need = cap_units + cap_units * GROSS_MARGIN_PCT // 100 + 1    # gross must beat the gas cap with a 10 pct margin
    min_profit = need
    log('opportunity', trigger=trigger, route=route, table=table, amount_usdc_units=amount, gross_usdc_units=gross,
        base_fee=base_fee, eth_usd=price, gas_estimate=est, gas_limit=gas_limit, max_fee=max_fee, priority=tip,
        gas_cap_wei=cap_wei, gas_cap_usdc_units=cap_units, min_profit_usdc_units=min_profit)
    if max_fee > MAX_FEE_WEI or gas_limit > MAX_GAS_LIMIT or cap_wei / 1e18 * ETH_REF_USD >= MAX_TX_USD:
        log('opportunity_skip', route=route, reason='fee_gas_or_usd_cap', max_fee=max_fee, gas_limit=gas_limit,
            gas_cap_usd_at_ref=cap_wei / 1e18 * ETH_REF_USD)
        return False
    if gross < need:
        log('opportunity_skip', route=route, reason='gross_below_gas_cap', gross_usdc_units=gross, need_usdc_units=need)
        return None     # None = below the cap: check() backs off until the gain grows
    if s.setdefault('cooldown', {}).get(route, 0) > now:
        log('opportunity_skip', route=route, reason='cooldown')
        return False
    data = calldata(route, amount, min_profit)
    checked = try_sim(data, ctx, gas_limit)      # the exact guarded call at the signed gas limit
    if not checked:
        log('simulate_revert', route=route, amount_usdc_units=amount, min_profit_usdc_units=min_profit, gas_limit=gas_limit)
        return False
    s['cooldown'][route] = now + SEND_COOLDOWN
    if MODE == 'live':
        # OP Stack loss bound: one send can cost at most the wallet's native balance, which must be worth under 1 USD.
        balance = int(rpc('eth_getBalance', [ctx[0], 'latest']), 16)
        ok, reason, usd = wallet_bound(balance, price, cap_wei)
        if not ok:
            log('opportunity_skip', route=route, reason=reason, wallet_wei=balance, wallet_usd=usd, eth_usd=price,
                wallet_max_usd=WALLET_MAX_USD, gas_cap_wei=cap_wei)
            return False
        log('wallet_bound', route=route, wallet_wei=balance, wallet_usd=usd, eth_usd=price, wallet_max_usd=WALLET_MAX_USD)
        send_live(route, data, gas_limit, max_fee, tip, checked, min_profit, cap_wei, amount, price)
    else:
        log('paper_sim', result='success', route=route, amount_usdc_units=amount, gross_usdc_units=checked,
            min_profit_usdc_units=min_profit, gas_limit=gas_limit, max_fee=max_fee, priority=tip, gas_cap_wei=cap_wei,
            gas_cap_usd=cap_wei / 1e18 * price, net_usd_at_cap=checked / 1e6 - cap_wei / 1e18 * price, eth_usd=price,
            wallet_max_usd=WALLET_MAX_USD)
    return True


def check(s, trigger):
    """One look at the chain: probe both directions at every size, act on the best gain.
    Returns the gain (USDC units) left standing unsent; 0 if there is none or it was sent / paper-simulated."""
    now = time.time()
    s['last_check'] = now
    ctx = exec_ctx()
    gains = probe_all(ctx)
    if not gains:
        log('check', trigger=trigger, reason='nothing_to_take')
        return 0
    (route, size), gross = max(gains.items(), key=lambda x: x[1])
    table = {f'{r}:{u}': g for (r, u), g in gains.items()}
    # Read budget: a small gain can stand for hours. No further reads for a gain that cannot cover any signed cap,
    # nor for one that was just found below the cap and has not grown by 3 pct (re-examined after 5 minutes).
    if gross < MIN_GROSS_UNITS:
        log('check', trigger=trigger, reason='gain_below_gas', best=f'{route}:{size}', gross_usdc_units=gross)
        return gross
    skip = s.get('below_cap') or {}
    if skip.get('route') == route and gross * 100 <= skip.get('gross', 0) * 103 and now < skip.get('until', 0):
        log('check', trigger=trigger, reason='gain_unchanged_below_cap', best=f'{route}:{size}', gross_usdc_units=gross)
        return gross
    s['below_cap'] = None
    done = take(s, route, size, gross, trigger, ctx, now, table)
    if done is None:
        s['below_cap'] = {'route': route, 'gross': gross, 'until': now + 300}
    return 0 if done else gross


def feed_wait(cursor, timeout):
    """Long-poll the farm feed for Swap on the jEUR/USDC pool (one filter: one address, one topic0). Returns the feed's
    JSON ({'cursor', 'logs'} plus 'timeout' or 'gap'). HTTP 429 / 503 and connection errors raise (the caller re-reads)."""
    q = {'address': POOL_JEUR, 'topic0': SWAP_TOPIC, 'timeout': str(int(timeout))}
    if cursor:
        q['after'] = cursor
    url = f'{FEED}/logs/{CHAIN}?' + urllib.parse.urlencode(q)
    with urllib.request.urlopen(url, timeout=timeout + 15) as resp:
        return json.load(resp)


def look(s, trigger):
    """check() plus the follow-up schedule: a gain left standing below the send line is looked at again after
    FOLLOW_UPS seconds (the EURC/USDC pool keeps moving and is not on the feed). A follow-up look arms nothing."""
    standing = check(s, trigger)
    if trigger != 'follow_up':
        s['follow_ups'] = [time.time() + d for d in FOLLOW_UPS] if standing else []


def load_state():
    try:
        return json.loads(STATE.read_text())
    except Exception:
        return {'last_check': 0, 'cooldown': {}}


def save_state(s):
    tmp = STATE.with_suffix('.tmp')
    tmp.write_text(json.dumps(s, separators=(',', ':')))
    tmp.replace(STATE)


def main():
    """Wait on the feed; look on an event, on a gap / removed log / feed error (state re-read), on the safety poll and
    on the bounded follow-ups. Every relay read is inside the try that catches the bot's CU cap."""
    s = load_state()
    s['feed_cursor'] = None       # a restart subscribes afresh and re-reads state once ('start' look)
    s['follow_ups'] = []
    s['last_check'] = 0
    log('start', mode=MODE, executor=(EXEC if MODE == 'live' else PAPER_EXEC), wrapper=WRAPPER, routes=list(ROUTES),
        sizes_usdc=list(SIZES_USDC), trigger='feed Swap', feed_address=POOL_JEUR, feed_topic0=SWAP_TOPIC,
        safety_poll_seconds=SAFETY_POLL, follow_ups=list(FOLLOW_UPS))
    feed_down_until = 0
    while True:
        try:
            now = time.time()
            ups = s.get('follow_ups') or []
            if ups and now >= ups[0]:
                s['follow_ups'] = ups[1:]
                look(s, 'follow_up')
            elif now - s.get('last_check', 0) >= SAFETY_POLL:
                look(s, 'safety_poll' if s.get('last_check') else 'start')
            elif now < feed_down_until:
                time.sleep(min(feed_down_until - now, 5))
                continue
            else:
                due = min([s['last_check'] + SAFETY_POLL] + ups[:1])
                try:
                    result = feed_wait(s.get('feed_cursor'), max(1, min(FEED_TIMEOUT, due - now)))
                except (urllib.error.URLError, OSError, ValueError) as e:
                    # 429 (filter slots or CU cap) / 503 / connection error: something may have been missed. Re-read
                    # state once now, then leave the feed alone for FEED_DOWN_POLL seconds.
                    log('feed_error', error=str(e)[:180])
                    feed_down_until = time.time() + FEED_DOWN_POLL
                    look(s, 'feed_error')
                    save_state(s)
                    continue
                first = s.get('feed_cursor') is None
                s['feed_cursor'] = result.get('cursor', s.get('feed_cursor'))
                logs = result.get('logs') or []
                if result.get('gap') or any(x.get('removed') for x in logs):
                    log('feed_gap', gap=bool(result.get('gap')), removed=sum(1 for x in logs if x.get('removed')))
                    look(s, 'feed_gap')
                elif logs:
                    log('feed', events=len(logs), blocks=sorted({int(x['blockNumber'], 16) for x in logs}),
                        txs=sorted({x['transactionHash'] for x in logs})[:4],
                        block_ts=[x.get('blockTimestamp') for x in logs][:4])
                    look(s, 'feed')
                elif first:
                    log('feed_subscribed', cursor=s['feed_cursor'])
        except ReadBudgetExceeded as e:
            log('read_budget', error=str(e))
            s['follow_ups'] = []
            time.sleep(600)
        except Exception as e:
            log('loop_error', error=str(e)[:250])
            s['last_check'] = time.time()
            time.sleep(5)
        save_state(s)


if __name__ == '__main__':
    main()
