#!/usr/bin/env python3
"""trial-aave-bsc: cheap-chain trial of Aave v3 liquidations on BNB Smart Chain.

Waits on the farm feed for Pool LiquidationCall logs (a price flip that liquidates one user usually
puts others under water) plus a 60 s safety scan of the near-HF list. For an underwater user it
simulates the exact executor call (Aave flashLoanSimple -> liquidationCall -> PancakeSwap V3 swap ->
repay with premium -> optional exit swap of the gain to USDC) and, in live mode, sends it when the
simulated gross > the signed gas cap. A lost attempt costs gas only.
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
CHAIN = 'bsc'
FEED = 'http://127.0.0.1:8546/logs/bsc'

POOL = '0x6807dc923806fe8fd134338eabca509979a7e0cb'       # Aave v3 Pool (BNB chain, bgd-labs aave-address-book AaveV3BNB)
ROUTER = '0x1b81d678ffb9c0263b24a97847620c99d213eb14'     # PancakeSwap V3 SwapRouter (pancake-v3-contracts deployments/bscMainnet.json)
MULTICALL = '0xca11bde05977b3631167028862be2a173976ca11'
WBNB = '0xbb4cdb9cbd36b01bd1cbaebf2de08d9173bc095c'
USDC = '0x8ac76a51cc950d9822d68b83fe1ad97b32cd580d'       # 18 decimals on BSC
USDT = '0x55d398326f99059ff775485246999027b3197955'       # 18 decimals
BTCB = '0x7130d2a12b9bcbfae4f2634d864a1ee1ce3ead9c'
ETH = '0x2170ed0880ac9a755fd29b2688956bd959f933f8'
# debt token -> (pay token, exit fee tier debt -> pay token, unwrap). The bot wallet is paid in USDC or native BNB.
DEBTS = {USDC: (USDC, 0, False), USDT: (USDC, 100, False), WBNB: (WBNB, 0, True)}
COLLATERALS = (BTCB, WBNB, ETH, USDT, USDC)
# Share of the user's total debt offered as cover. Aave caps the repayment at the close factor (over-cover goes
# straight back with the flash loan); a cover that leaves dust reverts (fork proof: 50%, 25%, 10% of a 210 USD
# debt revert, 103% succeeds), and a cover above what the chosen collateral can pay for reverts for a user
# with several collaterals, so smaller covers are simulated too.
COVER_SHARES = (1.03, 0.5, 0.25, 0.15, 0.07, 0.02)
FEES = (500, 100, 2500)              # PancakeSwap V3 fee tiers tried for collateral -> debt
LIQ_TOPIC = '0xe413a321e8681d831f4dbccbca790d2952b56f977908e45be37335533e005286'
BORROW_TOPIC = '0xb3d084820fb1a9decffb176436bd02558d15fac9b0ddfed8c465bc7359d7dce0'
WITHDRAW_TOPIC = '0x3115d1449a7b732c986cba18244e897a450f61e1bb8d589cd2e69e6c8924f9f7'
# liquidate(address,(address,address,address,address,address,uint24,address,uint24),uint256,uint256,bool)
SEL_LIQUIDATE = '0x286232cc'

PAPER_EXEC = '0xb464f7314d55ec6a9a0cf6f7f6df17af8ed5b352'   # fork deployment; paper code override only
PAPER_OWNER = '0xc0ffee0000000000000000000000000000000001'
EXEC = os.environ.get('EXECUTOR_ADDR_BSC') or os.environ.get('EXECUTOR_ADDR')
if MODE == 'live' and not EXEC:
    raise SystemExit('EXECUTOR_ADDR_BSC or EXECUTOR_ADDR is required in live mode')
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
MAX_TX_USD = 0.90            # signed gas cap (gas price x gasLimit) stays under this
MAX_FEE_WEI = 3_000_000_000  # 3 gwei absolute ceiling for the gas price
MAX_GAS_LIMIT = 3_000_000
BID_SHARE = 0.50             # gas bid: at most this share of the simulated gross
MAX_SIMS = 40                # simulations per underwater user
MAX_COVER_USD = 150_000      # flash-loaned from the Aave pool, never the bot's own funds
MIN_DEBT_BASE = 5 * 10**8    # skip users with less than 5 USD of debt (Aave base currency, 8 decimals)
RELAY_CU_CAP = 75_000        # per UTC day; the feed's own CU is metered separately

NEAR_COUNT = 200
SCAN_INTERVAL = 3600
POLL_INTERVAL = 50         # with the 55 s feed timeout the safety cadence is ~55-60 s
DISCOVER_INTERVAL = 600
CU_COST = {'eth_call': 26, 'eth_estimateGas': 20, 'eth_getLogs': 75, 'eth_getTransactionReceipt': 20,
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


def aggregate(users):
    """One Multicall3 tryAggregate(false, calls) of Pool.getUserAccountData(user). Returns [(debtBase, hf)]."""
    calls = ['0xbf92857c' + aword(a) for a in users]
    starts, acc = [], 32 * len(calls)
    for data in calls:
        starts.append(acc)
        size = (len(data) - 2) // 2
        acc += 96 + ((size + 31) // 32) * 32
    enc = '0xbce38bd7' + word(0) + word(64) + word(len(calls)) + ''.join(word(x) for x in starts)
    for data in calls:
        size = (len(data) - 2) // 2
        enc += aword(POOL) + word(64) + word(size) + data[2:].ljust(((size + 31) // 32) * 64, '0')
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
        data = '0x' + h[start + off * 2 + 64:start + off * 2 + 64 + length * 2]
        out.append((at(data, 1), at(data, 5)) if ok and len(data) >= 2 + 6 * 64 else (0, 0))
    return out + [(0, 0)] * (len(users) - len(out))


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


def reserves():
    h = call(POOL, '0xd1946dbc')  # getReservesList()
    n = at(h, 1)
    if not 1 <= n <= 128:
        raise RuntimeError(f'bad reserve count {n}')
    return {addr_of(h[2 + (2 + i) * 64:2 + (3 + i) * 64]): i for i in range(n)}


def bnb_price_usd():
    provider = addr_of(call(POOL, '0x0542975c'))       # ADDRESSES_PROVIDER()
    oracle = addr_of(call(provider, '0xfca513a8'))     # getPriceOracle()
    return at(call(oracle, '0xb3596f07' + aword(WBNB)), 0) / 1e8  # getAssetPrice(WBNB)


def calldata(user, coll, debt, fee, cover, min_profit):
    pay, pay_fee, unwrap = DEBTS[debt]
    return (SEL_LIQUIDATE + aword(POOL) + aword(POOL) + aword(user) + aword(coll) + aword(debt)
            + aword(ROUTER) + word(fee) + aword(pay) + word(pay_fee) + word(cover) + word(min_profit)
            + word(int(unwrap)))


def exec_ctx():
    if MODE == 'live':
        return bot_address(), EXEC, None
    return PAPER_OWNER, PAPER_EXEC, {PAPER_EXEC: {'code': RUNTIME}}


def sim(data, ctx):
    frm, to, ov = ctx
    params = [{'from': frm, 'to': to, 'data': data, 'gas': hex(MAX_GAS_LIMIT)}, 'latest'] + ([ov] if ov else [])
    return at(rpc('eth_call', params), 0)


def estimate(data, ctx):
    frm, to, ov = ctx
    params = [{'from': frm, 'to': to, 'data': data}, 'latest'] + ([ov] if ov else [])
    return int(rpc('eth_estimateGas', params), 16)


def gross_usd_of(debt, gain, bnb_usd):
    """The gain is in the pay token: native BNB for WBNB debt, USDC (18 decimals) otherwise."""
    return gain / 1e18 * bnb_usd if DEBTS[debt][2] else gain / 1e18


def winner_block(user, send_block, our_hash):
    """Block of the LiquidationCall that took this user near our send (ours if we won)."""
    head = int(rpc('eth_blockNumber', []), 16)
    logs = rpc('eth_getLogs', [{'address': POOL, 'fromBlock': hex(max(0, send_block - 600)), 'toBlock': hex(head),
                                'topics': [LIQ_TOPIC, None, None, '0x' + aword(user)]}])
    ours = [int(x['blockNumber'], 16) for x in logs if x['transactionHash'].lower() == our_hash.lower()]
    if ours:
        return min(ours), None
    if not logs:
        return None, None
    first = min(logs, key=lambda x: int(x['blockNumber'], 16))
    return int(first['blockNumber'], 16), first['transactionHash']


def send_live(user, coll, debt, data, gas_limit, gas_price, gross_usd, gas_cap_usd):
    import farmbot_signer
    # BSC has a zero base fee: the price paid is the priority fee, so both fields carry the same capped price.
    reply = farmbot_signer.send(CHAIN, EXEC, data, 0, gas_limit, gas_price, max_priority_fee_per_gas=gas_price)
    h = None
    if isinstance(reply, dict):
        h = reply.get('txHash') or reply.get('tx_hash') or reply.get('hash')
    if not h:
        log('signer_reject', user=user, debt=debt, collateral=coll, reply=reply)  # final, never retried
        return
    log('send', hash=h, user=user, debt=debt, collateral=coll, gas_limit=gas_limit, max_fee=gas_price,
        priority=gas_price, gross_usd=gross_usd, gas_cap_usd=gas_cap_usd, executor=EXEC)
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
    cost = used * int(receipt['effectiveGasPrice'], 16)
    try:
        wb, wtx = winner_block(user, b, h)
    except Exception:
        wb, wtx = None, None
    log('send_result', hash=h, user=user, debt=debt, collateral=coll, result='won' if status else 'lost',
        gas_used=used, gas_cost_wei=cost, send_block=b, winner_block=wb, winner_tx=wtx,
        blocks_after_winner=(b - wb if wb is not None else None), gross_usd=gross_usd)


def attempt(s, user, hf, debt_base, idx, trigger):
    now = time.time()
    if s['cooldown'].get(user, 0) > now:
        return
    s['cooldown'][user] = now + 600
    cfg = at(call(POOL, '0x4417a583' + aword(user)), 0)  # getUserConfiguration(user)
    debts = [t for t in DEBTS if t in idx and cfg >> (2 * idx[t]) & 1]
    colls = [t for t in COLLATERALS if t in idx and cfg >> (2 * idx[t] + 1) & 1]
    if not debts or not colls:
        log('opportunity_skip', user=user, hf=hf, reason='unsupported_assets', trigger=trigger)
        return
    bnb_usd = bnb_price_usd()
    if bnb_usd <= 0:
        return
    ctx = exec_ctx()
    # Speed first (0.45 s blocks): the first combination that simulates is taken. Order: the main fee tier (500)
    # for every debt/collateral pair at the largest covers (over-cover of the whole debt: Aave caps the repayment,
    # the rest of the flash loan goes straight back; a cover that leaves dust reverts), then the other fee tiers
    # and the small covers. At most MAX_SIMS simulations per user.
    pairs = [(d, c) for d in debts for c in colls]
    first = [(d, c, 0 if c == d else FEES[0], sh) for sh in COVER_SHARES[:3] for d, c in pairs]
    rest = [(d, c, f, sh) for sh in COVER_SHARES for d, c in pairs for f in ((0,) if c == d else FEES)]
    combos = first + [x for x in rest if x not in first]
    best, reverts = None, 0
    for debt, coll, fee, share in combos[:MAX_SIMS]:
        usd = min(debt_base / 1e8 * share + (1 if share > 1 else 0), MAX_COVER_USD)
        cover = int(usd / bnb_usd * 1e18) if debt == WBNB else int(usd * 1e18)
        if cover <= 0:
            continue
        try:
            gain = sim(calldata(user, coll, debt, fee, cover, 0), ctx)
        except ReadBudgetExceeded:
            raise
        except Exception as e:
            reverts += 1
            last_error = str(e)[:160]
            continue
        best = (gross_usd_of(debt, gain, bnb_usd), debt, coll, fee, cover, gain)
        break
    if best is None:
        log('simulate_revert', user=user, hf=hf, debts=debts, collaterals=colls, tried=reverts,
            error=last_error if reverts else 'no combination')
        return
    gross_usd, debt, coll, fee, cover, gain = best
    try:
        gas_limit = min(MAX_GAS_LIMIT, estimate(calldata(user, coll, debt, fee, cover, 0), ctx) * 5 // 4)
        base_price = int(rpc('eth_gasPrice', []), 16)
    except ReadBudgetExceeded:
        raise
    except Exception as e:
        log('simulate_revert', user=user, debt=debt, collateral=coll, fee=fee, hf=hf, error='estimate: ' + str(e)[:140])
        return
    # Price ceiling so that gasPrice x gasLimit < MAX_TX_USD (and never above 3 gwei).
    fee_ceiling = min(MAX_FEE_WEI, int(MAX_TX_USD / bnb_usd * 1e18 / gas_limit) - 1)
    bid = int(gross_usd * BID_SHARE / bnb_usd * 1e18 / gas_limit)       # bid <= BID_SHARE of gross
    gas_price = min(fee_ceiling, max(base_price, bid))
    gas_cap_usd = gas_limit * gas_price / 1e18 * bnb_usd
    if gas_price < base_price or gas_cap_usd >= MAX_TX_USD or gross_usd <= gas_cap_usd:
        log('opportunity_skip', user=user, debt=debt, collateral=coll, hf=hf, gross_usd=gross_usd,
            gas_cap_usd=gas_cap_usd, reason='gross_not_above_gas_cap', trigger=trigger)
        return
    # On-chain floor: the executor reverts unless the gain (pay token) covers the signed gas cap.
    min_profit = int(gas_cap_usd / bnb_usd * 1e18) + 1 if DEBTS[debt][2] else int(gas_cap_usd * 1e18) + 1
    data = calldata(user, coll, debt, fee, cover, min_profit)
    try:
        gain = sim(data, ctx)  # the exact bytes that would be sent
    except ReadBudgetExceeded:
        raise
    except Exception as e:
        log('simulate_revert', user=user, debt=debt, collateral=coll, fee=fee, hf=hf, error='final: ' + str(e)[:140])
        return
    log('opportunity', user=user, debt=debt, collateral=coll, fee=fee, hf=hf, cover=cover, gross_usd=gross_usd,
        gas_cap_usd=gas_cap_usd, gas_limit=gas_limit, max_fee=gas_price, priority=gas_price, min_profit=min_profit,
        simulated_gain=gain, trigger=trigger, mode=MODE)
    if MODE == 'live':
        send_live(user, coll, debt, data, gas_limit, gas_price, gross_usd, gas_cap_usd)
    else:
        log('paper_sim', user=user, debt=debt, collateral=coll, result='success', gain=gain, gross_usd=gross_usd)


def scan_users(s, users, idx, label):
    eligible, near = [], []
    for off in range(0, len(users), 200):
        batch = users[off:off + 200]
        try:
            data = aggregate(batch)
        except ReadBudgetExceeded:
            raise
        except Exception as e:
            log('scan_error', label=label, offset=off, error=str(e)[:200])
            continue
        for a, (debt, hf) in zip(batch, data):
            if debt >= MIN_DEBT_BASE and hf > 0:
                near.append((hf, a))
                if hf < 10**18:
                    eligible.append((debt, hf, a))
    if label == 'full':
        near.sort(key=lambda z: abs(z[0] - 10**18))
        s['near'] = [a for _, a in near[:NEAR_COUNT]]
    log('scan', label=label, checked=len(users), debtors=len(near), underwater=len(eligible), near=len(s['near']))
    eligible.sort(reverse=True)  # largest debt first
    for debt, hf, a in eligible[:3]:
        attempt(s, a, hf / 1e18, debt, idx, label)


def discover(s):
    head = int(rpc('eth_blockNumber', []), 16)
    start = s['cursor_block'] + 1 if s['cursor_block'] is not None else head - 3000
    start = max(start, head - 4500)   # the relay serves at most 5000 BSC blocks per request (about 37 min)
    if start > head:
        return
    logs = rpc('eth_getLogs', [{'address': POOL, 'fromBlock': hex(start), 'toBlock': hex(head),
                                'topics': [[BORROW_TOPIC, WITHDRAW_TOPIC]]}])
    users = set(s['users'])
    fresh = set()
    for lg in logs:
        t = lg.get('topics', [])
        if len(t) > 2:   # Borrow: onBehalfOf = topics[2]; Withdraw: user = topics[2]
            a = addr_of(t[2])
            if a not in users:
                fresh.add(a)
    s['users'] = sorted(users | fresh)
    s['near'] = list(dict.fromkeys(s['near'] + sorted(fresh)))[:NEAR_COUNT + 100]  # new borrowers watched until next full scan
    s['cursor_block'] = head
    log('discover', from_block=start, to_block=head, logs=len(logs), added=len(fresh), universe=len(s['users']))


def feed_wait(cursor):
    q = {'address': POOL, 'topic0': LIQ_TOPIC, 'timeout': '55'}
    if cursor:
        q['after'] = cursor
    with urllib.request.urlopen(FEED + '?' + urllib.parse.urlencode(q), timeout=65) as r:
        return json.load(r)


def main():
    s = load_state()
    idx = reserves()
    if WBNB not in idx or USDC not in idx or USDT not in idx:
        raise SystemExit('Aave reserve list lacks WBNB/USDC/USDT')
    log('start', mode=MODE, executor=(EXEC if MODE == 'live' else PAPER_EXEC), universe=len(s['users']),
        reserve_index={t: idx.get(t) for t in (WBNB, USDC, USDT, BTCB, ETH)})
    while True:
        now = time.time()
        try:
            if now - s['last_discover'] >= DISCOVER_INTERVAL:
                s['last_discover'] = now
                discover(s)
            if now - s['last_scan'] >= SCAN_INTERVAL:
                s['last_scan'] = now
                scan_users(s, s['users'], idx, 'full')
            elif now - s['last_poll'] >= POLL_INTERVAL:
                s['last_poll'] = now
                scan_users(s, s['near'], idx, 'near')
            save_state(s)
            result = feed_wait(s.get('feed_cursor'))
            s['feed_cursor'] = result.get('cursor', s.get('feed_cursor'))
            logs = result.get('logs') or []
            if result.get('gap') or any(x.get('removed') for x in logs):
                scan_users(s, s['near'], idx, 'gap')
            elif logs:
                log('feed', events=len(logs), blocks=[x.get('blockNumber') for x in logs][:10])
                scan_users(s, s['near'], idx, 'liquidation_feed')
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
            log('feed_error', error=str(e)[:180])   # 429/503/timeout: fall back to a state re-read, then back off
            try:
                scan_users(s, s['near'], idx, 'gap')
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
