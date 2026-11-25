#!/usr/bin/env python3
"""trial-moonwell-base: cheap-chain trial of Moonwell (Base) core-market liquidations with USDC debt.

Waits on the farm feed for mUSDC LiquidateBorrow logs (one liquidation usually means a price move that
put other borrowers under water) plus timed scans of Comptroller.getAccountLiquidity over the known
mUSDC borrowers. For an account with a shortfall it simulates the exact executor call (Morpho flash
loan -> mUSDC.liquidateBorrow -> mCollateral.redeem -> UniV3 swap -> repay) and, in live mode, sends
it when the simulated gross > the signed gas cap. A lost attempt costs gas only.
"""
import sys
sys.path.append("/opt/farm/lib")  # live service does not put the signer library on the path
import datetime
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
MODE = os.environ.get('BOT_MODE', 'paper')
LANE = os.environ.get('RPC_LANE', 'paper')
RELAY = os.environ['RPC_RELAY_URL'].rstrip('/')
CHAIN = 'base'
FEED = 'http://127.0.0.1:8546/logs/base'

COMPTROLLER = '0xfbb21d0380bee3312b33c4353c8936a0f13ef26c'  # Moonwell Comptroller (Base)
MUSDC = '0xedc817a28e8b93b03976fbd4a3ddbc9f7d176c22'        # the debt market this trial repays
MWETH = '0x628ff693426583d9a7fb391e54366292f509d457'
MORPHO = '0xbbbbbbbbbb9cc5e90e3b3af64bdaf62c37eeffcb'       # Morpho Blue, fee-free flash loans
ROUTER = '0x2626664c2603336e57b271c5c0b26f421741e481'       # Uniswap V3 SwapRouter02 (Base)
MULTICALL = '0xca11bde05977b3631167028862be2a173976ca11'
WETH = '0x4200000000000000000000000000000000000006'
USDC = '0x833589fcd6edb6e08f4c7c32d4f71b54bda02913'
# Collateral markets with a direct UniV3 pool to USDC holding > 20k USDC on 2026-11-17
# (scratch/trial-moonwell-base/prep.json): mToken -> (underlying, fee tiers tried). mUSDC needs no swap.
ROUTES = {
    MWETH: (WETH, (500, 3000)),
    '0xf877acafa28c19b96727966690b2f44d35ad5976': ('0xcbb7c0000ab88b473b1f5afd9ef808440eed33bf', (500,)),    # cbBTC
    '0x73902f619ceb9b31fd8efecf435cbdf89e369ba6': ('0x940181a94a35a4569e4529a3cdfb74e38fd98631', (500,)),    # AERO
    '0xde8df9d942d78ede3ca06e60712582f79cfffc64': ('0x0b3e328455c4059eeb9e3f84b5543f74e24e7e1b', (3000,)),   # VIRTUAL
    '0x6308204872bdb7432df97b04b42443c714904f3e': ('0xbaa5cc21fd487b8fcc2f632f3f4e8d37262a0842', (10000,)),  # MORPHO
    '0xb4fb8fed5b3aaa8434f0b19b1b623d977e07e86d': ('0xcb585250f852c6c6bf90434ab21a00f02833a4af', (10000,)),  # cbXRP
    '0xd64bcb70c613a6d1f4d7d57ba64bb4a0767a9682': ('0xacfe6019ed1a7dc6f7b508c02d1b04ec88cc21bf', (3000,)),   # VVV
    '0xb682c840b5f4fc58b20769e691a6fa1305a501a2': ('0x60a3e35cc302bfa44cb288bc5a4f316fdb1adb42', (500,)),    # EURC
    MUSDC: (USDC, (0,)),
}
LIQ_TOPIC = '0x298637f684da70674f26509b10f07ec2fbc77a335ab1e7d6215a4b2484d8bb52'     # LiquidateBorrow(address,address,uint256,address,uint256)
BORROW_TOPIC = '0x13ed6866d4e1ee6da46f845c46d7e54120883d75c5ea9a2dacc1c4ca8984ab80'  # Borrow(address,uint256,uint256,uint256)
# liquidate(address,(address,address,address,address,address,address,uint24,address),uint256,uint256,bool)
SEL_LIQUIDATE = '0xa9ce24ff'
SEL_LIQUIDITY = '0x5ec88c79'      # getAccountLiquidity(address)
SEL_BORROW_BAL = '0x95dd9193'     # borrowBalanceStored(address)
SEL_ASSETS_IN = '0xabfceffc'      # getAssetsIn(address)
SEL_SNAPSHOT = '0xc37f68e2'       # getAccountSnapshot(address)
SEL_ORACLE = '0x7dc0d1d0'         # oracle()
SEL_PRICE = '0xfc57d4df'          # getUnderlyingPrice(address)
SEL_CLOSE = '0xe8755446'          # closeFactorMantissa()
SEL_INCENTIVE = '0x4ada90af'      # liquidationIncentiveMantissa()

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
SEED = json.loads((HERE / 'seed-users.json').read_text())

# ---- loss guard -----------------------------------------------------------------------------
MAX_TX_USD = 0.90            # signed gas cap (maxFeePerGas x gasLimit + L1 fee allowance) stays under this
L1_FEE_ALLOWANCE_USD = 0.02  # Base L1 data fee for ~450 bytes of calldata, generous
MAX_FEE_WEI = 500_000_000    # 0.5 gwei absolute ceiling for maxFeePerGas
BID_SHARE = 0.50             # priority fee bid: at most this share of the simulated gross
MAX_REPAY = 20_000_000_000   # 20,000 USDC, flash-loaned, never the bot's own funds
MIN_DEBT = 5_000_000         # skip accounts with less than 5 USDC of mUSDC debt
RELAY_CU_CAP = 80_000        # per UTC day; the feed's own CU is metered separately

NEAR_COUNT = 100
BATCH = 100                  # accounts per Multicall (2 sub-calls each)
SCAN_INTERVAL = 600
POLL_INTERVAL = 290          # near-list safety poll, about every 5 min
DISCOVER_INTERVAL = 600
CU_COST = {'eth_call': 26, 'eth_estimateGas': 20, 'eth_getLogs': 60, 'eth_getTransactionReceipt': 20,
           'eth_blockNumber': 10, 'eth_gasPrice': 20}
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


def at(h, i):
    return int(h[2 + i * 64:2 + (i + 1) * 64], 16)


def addr_of(h):
    return '0x' + h[-40:].lower()


def call(to, data):
    return rpc('eth_call', [{'to': to, 'data': data}, 'latest'])


def aggregate(calls):
    """One Multicall3 tryAggregate(false, [(target, data)]). Returns [(ok, '0x' + returndata)]."""
    starts, acc = [], 32 * len(calls)
    for _, data in calls:
        starts.append(acc)
        size = (len(data) - 2) // 2
        acc += 96 + ((size + 31) // 32) * 32
    enc = '0xbce38bd7' + word(0) + word(64) + word(len(calls)) + ''.join(word(x) for x in starts)
    for target, data in calls:
        size = (len(data) - 2) // 2
        enc += aword(target) + word(64) + word(size) + data[2:].ljust(((size + 31) // 32) * 64, '0')
    h = call(MULTICALL, enc)[2:]
    if len(h) < 128:
        raise RuntimeError('short Multicall answer')
    n = min(int(h[64:128], 16), len(calls))
    out = []
    for i in range(n):
        start = 128 + int(h[128 + i * 64:192 + i * 64], 16) * 2
        ok = int(h[start:start + 64], 16) != 0
        off = int(h[start + 64:start + 128], 16)
        length = int(h[start + off * 2:start + off * 2 + 64], 16)
        out.append((ok, '0x' + h[start + off * 2 + 64:start + off * 2 + 64 + length * 2]))
    return out + [(False, '0x')] * (len(calls) - len(out))


def account_data(users):
    """[(debt_usdc, liquidity_1e18, shortfall_1e18)] per user; (0, 0, 0) when a sub-call failed."""
    calls = []
    for a in users:
        calls.append((COMPTROLLER, SEL_LIQUIDITY + aword(a)))
        calls.append((MUSDC, SEL_BORROW_BAL + aword(a)))
    res = aggregate(calls)
    out = []
    for i in range(len(users)):
        (ok1, d1), (ok2, d2) = res[2 * i], res[2 * i + 1]
        if ok1 and ok2 and len(d1) >= 2 + 3 * 64 and len(d2) >= 2 + 64 and at(d1, 0) == 0:
            out.append((at(d2, 0), at(d1, 1), at(d1, 2)))
        else:
            out.append((0, 0, 0))
    return out


def load_state():
    if STATE.exists():
        try:
            return json.loads(STATE.read_text())
        except Exception:
            pass
    return {'users': SEED, 'near': [], 'cursor_block': None, 'feed_cursor': None,
            'last_scan': 0, 'last_poll': 0, 'last_discover': 0, 'cooldown': {}}


def save_state(s):
    now = time.time()
    s['cooldown'] = {k: v for k, v in s['cooldown'].items() if v > now}
    tmp = STATE.with_suffix('.tmp')
    tmp.write_text(json.dumps(s, separators=(',', ':')))
    tmp.replace(STATE)


def bot_address():
    import farmbot_signer
    a = farmbot_signer.my_address()
    a = a.get('address') if isinstance(a, dict) else a   # my_address() returns {"ok":..., "address":...}
    if not isinstance(a, str) or len(a) != 42:
        raise RuntimeError('signer my_address returned no address')
    return a


def oracle_address():
    return addr_of(call(COMPTROLLER, SEL_ORACLE))


def price_raw(oracle, mtoken):
    """Moonwell oracle price: USD x 1e(36 - underlying decimals)."""
    return at(call(oracle, SEL_PRICE + aword(mtoken)), 0)


def calldata(user, mcoll, coll, fee, repay, min_profit):
    return (SEL_LIQUIDATE + aword(MORPHO) + aword(MUSDC) + aword(user) + aword(mcoll) + aword(USDC) + aword(coll)
            + aword(ROUTER) + word(fee) + aword(WETH) + word(repay) + word(min_profit) + word(0))


def exec_ctx():
    if MODE == 'live':
        return bot_address(), EXEC, None
    return PAPER_OWNER, PAPER_EXEC, {PAPER_EXEC: {'code': RUNTIME}}


def sim(data, ctx):
    frm, to, ov = ctx
    params = [{'from': frm, 'to': to, 'data': data, 'gas': hex(4_000_000)}, 'latest'] + ([ov] if ov else [])
    return at(rpc('eth_call', params), 0)


def estimate(data, ctx):
    frm, to, ov = ctx
    params = [{'from': frm, 'to': to, 'data': data}, 'latest'] + ([ov] if ov else [])
    return int(rpc('eth_estimateGas', params), 16)


def winner_block(user, send_block, our_hash):
    """Block of the mUSDC LiquidateBorrow that took this borrower near our send (ours if we won)."""
    head = int(rpc('eth_blockNumber', []), 16)
    logs = rpc('eth_getLogs', [{'address': MUSDC, 'fromBlock': hex(max(0, send_block - 300)), 'toBlock': hex(head),
                                'topics': [LIQ_TOPIC]}])
    # LiquidateBorrow has no indexed fields: data = liquidator, borrower, repayAmount, mTokenCollateral, seizeTokens
    logs = [x for x in logs if len(x.get('data', '')) >= 2 + 5 * 64 and addr_of(x['data'][2 + 64:2 + 128]) == user.lower()]
    ours = [int(x['blockNumber'], 16) for x in logs if x['transactionHash'].lower() == our_hash.lower()]
    if ours:
        return min(ours), None
    if not logs:
        return None, None
    first = min(logs, key=lambda x: int(x['blockNumber'], 16))
    return int(first['blockNumber'], 16), first['transactionHash']


def send_live(user, mcoll, data, gas_limit, max_fee, priority, gross_usd, gas_cap_usd):
    import farmbot_signer
    reply = farmbot_signer.send(CHAIN, EXEC, data, 0, gas_limit, max_fee, max_priority_fee_per_gas=priority)
    h = None
    if isinstance(reply, dict):
        h = reply.get('txHash') or reply.get('tx_hash') or reply.get('hash')
    if not h:
        log('signer_reject', user=user, collateral_market=mcoll, reply=reply)  # final, never retried
        return
    log('send', hash=h, user=user, collateral_market=mcoll, gas_limit=gas_limit, max_fee=max_fee,
        priority=priority, gross_usd=gross_usd, gas_cap_usd=gas_cap_usd, executor=EXEC)
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
        log('send_result', hash=h, user=user, result='unknown', gas_used=None, winner_block=None)
        return
    b = int(receipt['blockNumber'], 16)
    status = int(receipt['status'], 16)
    used = int(receipt['gasUsed'], 16)
    cost = used * int(receipt['effectiveGasPrice'], 16) + int(receipt.get('l1Fee', '0x0'), 16)
    try:
        wb, wtx = winner_block(user, b, h)
    except Exception:
        wb, wtx = None, None
    log('send_result', hash=h, user=user, collateral_market=mcoll, result='won' if status else 'lost',
        gas_used=used, gas_cost_wei=cost, send_block=b, winner_block=wb, winner_tx=wtx,
        blocks_after_winner=(b - wb if wb is not None else None), gross_usd=gross_usd)


def attempt(s, user, debt, shortfall, trigger):
    now = time.time()
    s['cooldown'][user] = now + 6 * 3600   # shortened to 10 min below when a profitable route exists
    h = call(COMPTROLLER, SEL_ASSETS_IN + aword(user))
    n = at(h, 1)
    assets = [addr_of(h[2 + (2 + i) * 64:2 + (3 + i) * 64]) for i in range(min(n, 30))]
    markets = [m for m in assets if m in ROUTES]
    if not markets:
        log('opportunity_skip', user=user, shortfall=shortfall, reason='unsupported_collateral', trigger=trigger)
        return
    oracle = oracle_address()
    eth_usd = price_raw(oracle, MWETH) / 1e18
    close = at(call(COMPTROLLER, SEL_CLOSE), 0)
    incentive = at(call(COMPTROLLER, SEL_INCENTIVE), 0)
    if eth_usd <= 0 or not 0 < close <= 10**18 or incentive < 10**18:
        return
    snaps = aggregate([(m, SEL_SNAPSHOT + aword(user)) for m in markets])
    valued = []
    for m, (ok, d) in zip(markets, snaps):
        if not ok or len(d) < 2 + 4 * 64 or at(d, 0) != 0 or at(d, 1) == 0:
            continue
        underlying = at(d, 1) * at(d, 3) // 10**18                 # mToken balance x exchange rate
        value_usd = underlying * price_raw(oracle, m) / 1e36       # oracle price is USD x 1e(36 - decimals)
        if value_usd >= 1:
            valued.append((value_usd, m))
    valued.sort(reverse=True)
    if not valued:
        log('opportunity_skip', user=user, shortfall=shortfall, reason='no_supported_collateral_balance', trigger=trigger)
        return
    ctx = exec_ctx()
    max_repay = min(debt * close // 10**18 * 999 // 1000, MAX_REPAY)
    best = None
    for value_usd, m in valued[:2]:
        coll, fees = ROUTES[m]
        # the seize is repay x incentive at oracle prices and must fit in this collateral balance
        fit = int(value_usd * 1e6 * 10**18 / incentive * 0.98)
        for repay in dict.fromkeys((min(max_repay, fit), min(max_repay, fit) // 2)):
            if repay < 1_000_000:
                continue
            got = False
            for fee in fees:
                data = calldata(user, m, coll, fee, repay, 0)
                try:
                    gain = sim(data, ctx)
                except ReadBudgetExceeded:
                    raise
                except Exception as e:
                    log('simulate_revert', user=user, collateral_market=m, fee=fee, repay=repay, error=str(e)[:160])
                    continue
                got = True
                if best is None or gain > best[0]:
                    best = (gain, m, coll, fee, repay)
            if got:
                break   # the larger size works for this collateral; no need to try the half
    if best is None:
        return
    gain, m, coll, fee, repay = best
    gross_usd = gain / 1e6
    try:
        gas_limit = estimate(calldata(user, m, coll, fee, repay, 0), ctx) * 5 // 4
        base_price = int(rpc('eth_gasPrice', []), 16)
    except ReadBudgetExceeded:
        raise
    except Exception as e:
        log('simulate_revert', user=user, collateral_market=m, fee=fee, repay=repay, error='estimate: ' + str(e)[:140])
        return
    # Fee ceiling so that maxFeePerGas x gasLimit + L1 allowance < MAX_TX_USD (and never above 0.5 gwei).
    fee_ceiling = min(MAX_FEE_WEI, int((MAX_TX_USD - L1_FEE_ALLOWANCE_USD) / eth_usd * 1e18 / gas_limit))
    priority = int(gross_usd * BID_SHARE / eth_usd * 1e18 / gas_limit)       # bid <= BID_SHARE of gross
    priority = max(0, min(priority, fee_ceiling - 2 * base_price))
    max_fee = min(fee_ceiling, 2 * base_price + priority)
    gas_cap_usd = gas_limit * max_fee / 1e18 * eth_usd + L1_FEE_ALLOWANCE_USD
    if max_fee < base_price + priority or gas_cap_usd >= MAX_TX_USD or gross_usd <= gas_cap_usd:
        log('opportunity_skip', user=user, collateral_market=m, shortfall=shortfall, gross_usd=gross_usd,
            gas_cap_usd=gas_cap_usd, reason='gross_not_above_gas_cap', trigger=trigger)
        return
    # On-chain floor: the executor reverts unless the USDC gain covers the signed gas cap.
    min_profit = int(gas_cap_usd * 1e6) + 1
    data = calldata(user, m, coll, fee, repay, min_profit)
    try:
        gain = sim(data, ctx)  # the exact bytes that would be sent
    except ReadBudgetExceeded:
        raise
    except Exception as e:
        log('simulate_revert', user=user, collateral_market=m, fee=fee, repay=repay, error='final: ' + str(e)[:140])
        return
    s['cooldown'][user] = now + 600
    log('opportunity', user=user, collateral_market=m, collateral=coll, fee=fee, shortfall=shortfall, repay=repay,
        gross_usd=gross_usd, gas_cap_usd=gas_cap_usd, gas_limit=gas_limit, max_fee=max_fee, priority=priority,
        min_profit=min_profit, simulated_gain=gain, trigger=trigger, mode=MODE)
    if MODE == 'live':
        send_live(user, m, data, gas_limit, max_fee, priority, gross_usd, gas_cap_usd)
    else:
        log('paper_sim', user=user, collateral_market=m, result='success', gain=gain, gross_usd=gross_usd)


def scan_users(s, users, label):
    eligible, debtors = [], []
    for off in range(0, len(users), BATCH):
        batch = users[off:off + BATCH]
        try:
            data = account_data(batch)
        except ReadBudgetExceeded:
            raise
        except Exception as e:
            log('scan_error', label=label, offset=off, error=str(e)[:200])
            continue
        for a, (debt, liq, short) in zip(batch, data):
            if debt >= MIN_DEBT:
                debtors.append((liq - short, a))
                if short > 0:
                    eligible.append((debt, short, a))
    if label == 'full':
        debtors.sort()   # smallest excess liquidity first (under-water accounts lead)
        s['near'] = [a for _, a in debtors[:NEAR_COUNT]]
    log('scan', label=label, checked=len(users), debtors=len(debtors), underwater=len(eligible), near=len(s['near']))
    now = time.time()
    fresh = [x for x in sorted(eligible, reverse=True) if s['cooldown'].get(x[2], 0) <= now]  # largest debt first
    for debt, short, a in fresh[:3]:
        try:
            attempt(s, a, debt, short / 1e18, label)
        except ReadBudgetExceeded:
            raise
        except Exception as e:
            log('attempt_error', user=a, error=str(e)[:200])


def discover(s):
    head = int(rpc('eth_blockNumber', []), 16)
    start = s['cursor_block'] + 1 if s['cursor_block'] is not None else head - 3000
    start = max(start, head - 9000)   # at most ~30 min of 0.2 s blocks per request
    if start > head:
        return
    logs = rpc('eth_getLogs', [{'address': MUSDC, 'fromBlock': hex(start), 'toBlock': hex(head),
                                'topics': [BORROW_TOPIC]}])
    users = set(s['users'])
    fresh = set()
    for lg in logs:
        d = lg.get('data', '')
        if len(d) >= 2 + 64:   # Borrow has no indexed fields: borrower is data word 0
            a = addr_of(d[2:2 + 64])
            if a not in users:
                fresh.add(a)
    s['users'] = sorted(users | fresh)
    s['near'] = list(dict.fromkeys(s['near'] + sorted(fresh)))[:NEAR_COUNT]  # one Multicall for the near list
    s['cursor_block'] = head
    log('discover', from_block=start, to_block=head, logs=len(logs), added=len(fresh), universe=len(s['users']))


def feed_wait(cursor):
    q = {'address': MUSDC, 'topic0': LIQ_TOPIC, 'timeout': '55'}
    if cursor:
        q['after'] = cursor
    with urllib.request.urlopen(FEED + '?' + urllib.parse.urlencode(q), timeout=65) as r:
        return json.load(r)


def main():
    s = load_state()
    log('start', mode=MODE, executor=(EXEC if MODE == 'live' else PAPER_EXEC), universe=len(s['users']),
        oracle=oracle_address())
    while True:
        now = time.time()
        try:
            if now - s['last_discover'] >= DISCOVER_INTERVAL:
                s['last_discover'] = now
                discover(s)
            if now - s['last_scan'] >= SCAN_INTERVAL:
                s['last_scan'] = now
                s['last_poll'] = now
                scan_users(s, s['users'], 'full')
            elif now - s['last_poll'] >= POLL_INTERVAL:
                s['last_poll'] = now
                scan_users(s, s['near'], 'near')
            save_state(s)
            result = feed_wait(s.get('feed_cursor'))
            s['feed_cursor'] = result.get('cursor', s.get('feed_cursor'))
            logs = result.get('logs') or []
            if result.get('gap') or any(x.get('removed') for x in logs):
                scan_users(s, s['near'], 'gap')
            elif logs:
                log('feed', events=len(logs), blocks=[x.get('blockNumber') for x in logs][:10])
                scan_users(s, s['near'], 'liquidation_feed')
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
            log('feed_error', error=str(e)[:180])   # 429/503/timeout: fall back to a state re-read
            try:
                scan_users(s, s['near'], 'gap')
            except Exception as e2:
                log('scan_error', label='gap', error=str(e2)[:180])
            time.sleep(30)
        except ReadBudgetExceeded as e:
            log('read_budget', error=str(e))
            time.sleep(600)
        except Exception as e:
            log('loop_error', error=str(e)[:250])
            time.sleep(5)
        save_state(s)


if __name__ == '__main__':
    main()
