#!/usr/bin/env python3
"""Trial: Morpho Blue cbBTC/USDC liquidations on Base through the TrialMorphoTake executor.

Waits on the farm feed for the BTC/USD aggregator's update events, then checks the
borrowers nearest the threshold with one Multicall3 read, simulates the executor call
and (live) sends it. A lost attempt costs gas only (executor NoProfit guard).
"""
import sys as _farm_sys; _farm_sys.path.append("/opt/farm/lib")  # human 2026-11-17: signer import path
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
FEED = os.environ.get('FEED_URL', 'http://127.0.0.1:8546')
CHAIN = 'base'
MORPHO = '0xbbbbbbbbbb9cc5e90e3b3af64bdaf62c37eeffcb'
MARKET_ID = '9103c3b4e834476c9a62ea009ba2c884ee42e94e6e314a26f04d312434191836'
USDC = '0x833589fcd6edb6e08f4c7c32d4f71b54bda02913'
CBBTC = '0xcbb7c0000ab88b473b1f5afd9ef808440eed33bf'
ORACLE = '0x663becd10dae6c4a3dcd89f1d76c1174199639b9'
IRM = '0x46415998764c29ab2a25cbea6254146d50d22687'
LLTV = 860000000000000000
POOL = '0xfbb6eed8e7aa03b138556eedaf5d271a5e1e43ef'  # UniV3 USDC/cbBTC 0.05%
MULTICALL = '0xca11bde05977b3631167028862be2a173976ca11'
AGG = '0xe5ec87a39445b8d5b751b116802a53c5ae7e9df1'  # aggregator() of the oracle's BASE_FEED_1
T_ANSWER = '0x0559884fd3a460db3073b7fc896cc77986f16e378210ded43186175bf646fc5f'  # AnswerUpdated
T_OEV = '0x8d530b9ddc4b318d28fdd4c3a21fcfecece54c1a72a824f262985b99afef009b'  # update inside Atlas txs
T_LIQ = '0xa4946ede45d0c6f06a0f5ce92c9ad3b4751452d2fe0e25010783bcab57a67e41'  # Morpho Liquidate
SEL_TAKE = '0x8fb164a4'
SEL_POSITION = '0x93c52062'
SEL_MARKET = '0x5c60e39a'
SEL_PRICE = '0xa035b1fe'
SEL_TRYAGG = '0xbce38bd7'
PAPER_EXEC = '0xb464f7314d55ec6a9a0cf6f7f6df17af8ed5b352'
PAPER_OWNER = '0xc0ffee0000000000000000000000000000000001'
EXEC = os.environ.get('EXECUTOR_ADDR_BASE') or os.environ.get('EXECUTOR_ADDR')
if MODE == 'live' and not EXEC:
    raise SystemExit('EXECUTOR_ADDR_BASE or EXECUTOR_ADDR is required in live mode')
RUNTIME = (HERE / 'executor-runtime.hex').read_text().strip()
if not RUNTIME.startswith('0x'):
    raise SystemExit('missing paper executor runtime')
LOG = HERE / 'logs' / 'bot.jsonl'
STATE = HERE / 'state' / 'state.json'
CU_FILE = HERE / 'state' / 'cu.json'
LOG.parent.mkdir(exist_ok=True)
STATE.parent.mkdir(exist_ok=True)
SEED = json.loads((HERE / 'seed-borrowers.json').read_text())

# ---- loss guard (trial rule: every send's gas cap < 1 USD) ----
GAS_LIMIT = 450_000            # fork: success 296,704, NoProfit revert 343,072
MAX_FEE_WEI = 500_000_000      # 0.5 gwei hard cap: 450k x 0.5 gwei = 2.25e-4 ETH
ETH_REF_USD = 4000.0           # deliberately high ETH price: cap = 0.90 USD at 4000 (0.41 at 1,818)
L1_FEE_USD = 0.02              # allowance for the OP-stack L1 data fee of a ~330-byte tx
BID_SHARE = 0.25               # priority fee bid is at most 25% of simulated gross
MAX_REPAY_USDC = 150_000 * 10**6   # size cap per take (pool depth); larger debts are taken in part
NEAR_COUNT = 400
FULL_SCAN_INTERVAL = 21600     # full scan every 6 h ...
FULL_SCAN_MIN_GAP = 1800       # ... or after a 1% oracle move, at most every 30 min
FULL_SCAN_MOVE = 0.01
SAFETY_POLL = 300
CU_COST = {'eth_call': 26, 'eth_getLogs': 75, 'eth_getTransactionReceipt': 20,
           'eth_blockNumber': 10, 'eth_gasPrice': 10}
CU_CAP = 80_000                # relay reads/day; the feed filter (~10k CU/day) is on top
_id = 0


class ReadBudgetExceeded(Exception):
    pass


def log(ev, **kw):
    row = {'ts': time.time(), 'ev': ev, **kw}
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
    if budget['cu'] + cost > CU_CAP:
        raise ReadBudgetExceeded(f'{CU_CAP} relay CU/day bot cap reached')
    budget['cu'] += cost
    CU_FILE.write_text(json.dumps(budget))
    _id += 1
    body = json.dumps({'jsonrpc': '2.0', 'id': _id, 'method': method, 'params': params}).encode()
    req = urllib.request.Request(f'{RELAY}/{CHAIN}?lane={LANE}', body, {'content-type': 'application/json'})
    with urllib.request.urlopen(req, timeout=30) as resp:
        ans = json.load(resp)
    if 'error' in ans:
        raise RuntimeError(f'{method}: {ans["error"]}')
    return ans['result']


def word(n):
    return format(n, '064x')


def aw(a):
    return a.lower().removeprefix('0x').zfill(64)


def at(h, i):
    return int(h[2 + i * 64:2 + (i + 1) * 64], 16)


def try_aggregate(calls):
    """Multicall3.tryAggregate(false, calls); calls = [(target, calldata hex)]. Returns [(ok, data hex)]."""
    starts, acc = [], 32 * len(calls)
    for _, data in calls:
        starts.append(acc)
        size = (len(data) - 2) // 2
        acc += 96 + ((size + 31) // 32) * 32
    enc = SEL_TRYAGG + word(0) + word(64) + word(len(calls)) + ''.join(word(x) for x in starts)
    for target, data in calls:
        size = (len(data) - 2) // 2
        enc += aw(target) + word(64) + word(size) + data[2:].ljust(((size + 31) // 32) * 64, '0')
    h = rpc('eth_call', [{'to': MULTICALL, 'data': enc}, 'latest'])[2:]
    if len(h) < 128:
        raise RuntimeError('short Multicall answer')
    n = int(h[64:128], 16)
    if n != len(calls):
        raise RuntimeError('Multicall length mismatch')
    out = []
    for i in range(n):
        start = 128 + int(h[128 + i * 64:192 + i * 64], 16) * 2
        ok = int(h[start:start + 64], 16) != 0
        off = int(h[start + 64:start + 128], 16)
        length = int(h[start + off * 2:start + off * 2 + 64], 16)
        out.append((ok, '0x' + h[start + off * 2 + 64:start + off * 2 + 64 + length * 2]))
    return out


def read_batch(users):
    """One eth_call: oracle price, market totals and position() of each user.
    Returns (price, totalBorrowAssets, totalBorrowShares, [(borrowShares, collateral)])."""
    calls = [(ORACLE, SEL_PRICE), (MORPHO, SEL_MARKET + MARKET_ID)]
    calls += [(MORPHO, SEL_POSITION + MARKET_ID + aw(u)) for u in users]
    res = try_aggregate(calls)
    if not res[0][0] or not res[1][0] or len(res[1][1]) < 2 + 6 * 64:
        raise RuntimeError('oracle or market read failed')
    price = at(res[0][1], 0)
    tba, tbs = at(res[1][1], 2), at(res[1][1], 3)
    pos = []
    for ok, data in res[2:]:
        if ok and len(data) >= 2 + 3 * 64:
            pos.append((at(data, 1), at(data, 2)))
        else:
            pos.append((0, 0))
    return price, tba, tbs, pos


def ratio(shares, coll, price, tba, tbs):
    """debt / maxBorrow from stored totals (interest since lastUpdate not included). > 1 = liquidatable."""
    if shares == 0:
        return 0.0, 0
    debt = shares * (tba + 1) // (tbs + 10**6)
    max_borrow = coll * price // 10**36 * LLTV // 10**18
    if max_borrow == 0:
        return 99.0, debt
    return debt / max_borrow, debt


def load_state():
    if STATE.exists():
        try:
            s = json.loads(STATE.read_text())
            if s.get('seed_n') == len(SEED):
                return s
        except Exception:
            pass
    return {'near': [], 'feed_cursor': None, 'last_full': 0, 'last_poll': 0, 'cooldown': {},
            'seed_n': len(SEED)}


def save_state(s):
    tmp = STATE.with_suffix('.tmp')
    tmp.write_text(json.dumps(s, separators=(',', ':')))
    tmp.replace(STATE)


def owner():
    import farmbot_signer
    a = farmbot_signer.my_address()
    a = a['address'] if isinstance(a, dict) else a
    if not isinstance(a, str) or len(a) != 42:
        raise RuntimeError('signer my_address returned no address')
    return a


def calldata(user, shares, min_profit):
    return (SEL_TAKE + aw(USDC) + aw(CBBTC) + aw(ORACLE) + aw(IRM) + word(LLTV)
            + aw(user) + word(shares) + aw(POOL) + word(min_profit))


def sim(user, shares, min_profit, from_addr, exec_addr, code):
    tx = {'from': from_addr, 'to': exec_addr, 'data': calldata(user, shares, min_profit), 'gas': hex(GAS_LIMIT)}
    params = [tx, 'latest'] + ([{exec_addr: {'code': code}}] if code else [])
    return at(rpc('eth_call', params), 0)


def winner_block(user, send_block, our_hash):
    lo = max(0, send_block - 50)
    hi = max(send_block, int(rpc('eth_blockNumber', []), 16))
    logs = rpc('eth_getLogs', [{'address': MORPHO, 'fromBlock': hex(lo), 'toBlock': hex(hi),
                               'topics': [T_LIQ, '0x' + MARKET_ID, None, '0x' + aw(user)]}])
    ours = [int(x['blockNumber'], 16) for x in logs if x['transactionHash'].lower() == our_hash.lower()]
    if ours:
        return min(ours)
    return min((int(x['blockNumber'], 16) for x in logs), default=None)


def send_live(user, data, max_fee, priority, gross_usd):
    import farmbot_signer
    reply = farmbot_signer.send(CHAIN, EXEC, data, 0, GAS_LIMIT, max_fee, max_priority_fee_per_gas=priority)
    h = reply.get('txHash') if isinstance(reply, dict) else None
    if not h:
        log('signer_reject', user=user, reply=reply)  # final: no retry
        return
    receipt = None
    for _ in range(30):  # base blocks are 0.2 s; give up after 15 s
        time.sleep(0.5)
        receipt = rpc('eth_getTransactionReceipt', [h])
        if receipt:
            break
    if not receipt:
        log('send_result', hash=h, user=user, result='unknown', gas_used=None, winner_block=None)
        return
    b = int(receipt['blockNumber'], 16)
    status = int(receipt['status'], 16)
    used = int(receipt['gasUsed'], 16)
    price = int(receipt['effectiveGasPrice'], 16)
    l1 = int(receipt.get('l1Fee') or '0x0', 16)
    try:
        winner = winner_block(user, b, h)
    except Exception:
        winner = None
    log('send_result', hash=h, user=user, result='won' if status else 'lost', gas_used=used,
        gas_cost_wei=used * price + l1, l1_fee_wei=l1, winner_block=winner, send_block=b,
        blocks_after_winner=(b - winner if winner is not None else None), gross_usd=gross_usd)


def attempt(s, user, shares, debt, r, why):
    now = time.time()
    if s['cooldown'].get(user, 0) > now:
        return
    s['cooldown'][user] = now + 600
    from_addr = owner() if MODE == 'live' else PAPER_OWNER
    exec_addr = EXEC if MODE == 'live' else PAPER_EXEC
    code = None if MODE == 'live' else RUNTIME
    # full debt, or the part under the size cap; one smaller retry if the pool cannot absorb it
    sizes = [shares if debt <= MAX_REPAY_USDC else shares * MAX_REPAY_USDC // debt]
    sizes.append(sizes[0] // 8)
    for size in sizes:
        if size == 0:
            continue
        try:
            gain = sim(user, size, 1, from_addr, exec_addr, code)
        except ReadBudgetExceeded:
            raise
        except Exception as e:
            log('simulate_revert', user=user, why=why, ratio=r, shares=size, error=str(e)[:200])
            if 'healthy' in str(e):
                s['cooldown'][user] = now + 20      # borderline: look again on the next update
                return
            s['cooldown'][user] = now + 21600       # unsellable / bad debt: do not burn reads on it
            continue
        gross_usd = gain / 1e6
        base_fee = int(rpc('eth_gasPrice', []), 16)
        priority = int(gross_usd * BID_SHARE / ETH_REF_USD * 1e18 / GAS_LIMIT)
        max_fee = min(MAX_FEE_WEI, base_fee * 2 + priority)
        priority = min(priority, max_fee)
        gas_cap_usd = GAS_LIMIT * max_fee / 1e18 * ETH_REF_USD + L1_FEE_USD
        if max_fee < base_fee or gas_cap_usd >= 1.0 or gross_usd <= gas_cap_usd:
            log('opportunity_skip', user=user, why=why, ratio=r, gross_usd=gross_usd,
                gas_cap_usd=gas_cap_usd, base_fee=base_fee, reason='gross_not_above_gas_cap')
            return
        min_profit = int(gas_cap_usd * 1e6)
        data = calldata(user, size, min_profit)
        try:
            gain = sim(user, size, min_profit, from_addr, exec_addr, code)  # the exact bytes to send
        except ReadBudgetExceeded:
            raise
        except Exception as e:
            log('simulate_revert', user=user, why=why, ratio=r, shares=size, error=str(e)[:200])
            return
        log('opportunity', user=user, why=why, ratio=r, shares=size, debt_usdc=debt / 1e6,
            gross_usd=gross_usd, gas_cap_usd=gas_cap_usd, max_fee=max_fee, priority=priority,
            simulated_gain=gain, mode=MODE)
        if MODE == 'live':
            send_live(user, data, max_fee, priority, gross_usd)
        else:
            log('paper_sim', user=user, result='success', gain=gain)
        return


def scan(s, users, label):
    rows = []
    price = None
    for off in range(0, len(users), 200):
        batch = users[off:off + 200]
        try:
            price, tba, tbs, pos = read_batch(batch)
        except ReadBudgetExceeded:
            raise
        except Exception as e:
            log('scan_error', label=label, offset=off, error=str(e)[:200])
            continue
        for u, (shares, coll) in zip(batch, pos):
            if shares > 0:
                r, debt = ratio(shares, coll, price, tba, tbs)
                rows.append((r, u, shares, debt))
    if label == 'full':
        near = sorted(rows, key=lambda z: abs(z[0] - 1.0))[:NEAR_COUNT]
        s['near'] = [u for _, u, _, _ in near]
        if price:
            s['full_price'] = str(price)
    if price:
        s['last_price'] = str(price)
    # stored totals lag accrued interest slightly: simulate everything from 0.9998 up
    cands = sorted([z for z in rows if 0.9998 <= z[0] < 50], key=lambda z: -z[3])
    log('scan', label=label, checked=len(users), debtors=len(rows), candidates=len(cands),
        near=len(s['near']), top_ratio=max((z[0] for z in rows if z[0] < 50), default=None))
    for r, u, shares, debt in cands[:5]:
        attempt(s, u, shares, debt, r, label)


def full_scan_due(s, now):
    if not s['near'] or now - s['last_full'] >= FULL_SCAN_INTERVAL:
        return True
    try:
        moved = abs(int(s['last_price']) / int(s['full_price']) - 1.0)
    except Exception:
        return False
    return moved >= FULL_SCAN_MOVE and now - s['last_full'] >= FULL_SCAN_MIN_GAP


def feed_wait(cursor):
    q = {'address': AGG, 'topic0': f'{T_ANSWER},{T_OEV}', 'timeout': '55'}
    if cursor:
        q['after'] = cursor
    with urllib.request.urlopen(f'{FEED}/logs/{CHAIN}?' + urllib.parse.urlencode(q), timeout=65) as r:
        return json.load(r)


def main():
    s = load_state()
    log('start', mode=MODE, seed=len(SEED), near=len(s['near']))
    while True:
        now = time.time()
        try:
            if full_scan_due(s, now):
                scan(s, SEED, 'full')
                s['last_full'] = s['last_poll'] = now
            elif now - s['last_poll'] >= SAFETY_POLL:
                scan(s, s['near'], 'safety_poll')
                s['last_poll'] = now
            s['cooldown'] = {u: t for u, t in s['cooldown'].items() if t > now}
            save_state(s)
            result = feed_wait(s.get('feed_cursor'))
            s['feed_cursor'] = result.get('cursor', s.get('feed_cursor'))
            if result.get('gap') or any(x.get('removed') for x in result.get('logs', [])):
                scan(s, s['near'], 'gap')
                s['last_poll'] = time.time()
            elif result.get('logs'):
                log('feed', events=len(result['logs']),
                    blocks=sorted({int(x['blockNumber'], 16) for x in result['logs']}),
                    topics=sorted({x['topics'][0][:10] for x in result['logs']}))
                scan(s, s['near'], 'oracle_update')
                s['last_poll'] = time.time()
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
            log('feed_error', error=str(e)[:180])
            try:
                scan(s, s['near'], 'gap')
                s['last_poll'] = time.time()
            except Exception as e2:
                log('scan_error', label='gap', error=str(e2)[:180])
            time.sleep(5)
        except ReadBudgetExceeded as e:
            log('read_budget', error=str(e))
            time.sleep(600)
        except Exception as e:
            log('loop_error', error=str(e)[:250])
            time.sleep(5)
        save_state(s)


if __name__ == '__main__':
    main()
