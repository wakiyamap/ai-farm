#!/usr/bin/env python3
"""Trial: Morpho Blue cbETH/USDC and WETH/USDC liquidations on Base through the
TrialMorphoRouteTake executor.

Waits on the farm feed for the two markets' price aggregators' update events, then checks
the borrowers nearest the threshold with one Multicall3 read per market, simulates the
executor call and (live) sends it. A lost attempt costs gas only (executor NoProfit guard).
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

HERE = Path(__file__).resolve().parent
MODE = os.environ.get('BOT_MODE', 'paper')
LANE = os.environ.get('RPC_LANE', 'paper')
RELAY = os.environ['RPC_RELAY_URL'].rstrip('/')
FEED = os.environ.get('FEED_URL', 'http://127.0.0.1:8546')
CHAIN = 'base'
MORPHO = '0xbbbbbbbbbb9cc5e90e3b3af64bdaf62c37eeffcb'
USDC = '0x833589fcd6edb6e08f4c7c32d4f71b54bda02913'
IRM = '0x46415998764c29ab2a25cbea6254146d50d22687'
MULTICALL = '0xca11bde05977b3631167028862be2a173976ca11'
POOL_CBETH_WETH = '0xa9dafa443a02fbc907cb0093276b3e6f4ef02a46'  # UniV3 cbETH/WETH 0.01%
POOL_WETH_USDC = '0xd0b53d9277642d899df5c87a3966a349a798f224'   # UniV3 WETH/USDC 0.05%
# Markets are data: id, params, the aggregator whose update moves the oracle, the sale
# route (collateral -> ... -> USDC) and a size cap that fits the route's depth.
MARKETS = {
    'cbeth': {
        'id': '0ca10126f6c94cbd9cf0a48cc9516ae5e3dec5aa68303e6d988ee37c5149bf0d',
        'coll': '0x2ae3f1ec7f1f5012cfeab0185bfc7aa3cf0dec22',
        'oracle': '0x97ff9cbd7e77348b2b8ffbb883bf29452ad18295',
        'lltv': 770000000000000000,
        'aggs': ['0x71e021bc2e8a709b72ac7b6036e5b2bf30f263d0'],  # aggregator() of CBETH/USD feed 0xd7818272
        'pools': [POOL_CBETH_WETH, POOL_WETH_USDC],
        'max_repay': 4_000 * 10**6,       # first hop holds ~7 cbETH + ~12 WETH: keep a take near 2 cbETH
    },
    'weth': {
        'id': '8793cf302b8ffd655ab97bd1c695dbd967807e8367a65cb2f4edaf1380ba1bda',
        'coll': '0x4200000000000000000000000000000000000006',
        'oracle': '0xfea2d58cefcb9fcb597723c6bae66ffe4193afe4',
        'lltv': 860000000000000000,
        # aggregator() of ETH/USD feed 0x71041ddd (base) and of USDC/USD feed 0x7e860098 (quote)
        'aggs': ['0x05c84a58fe042275b37db038baacd15f410c7bb0', '0x68be4c50235205ede361ac8244b1ee221cdda5e2'],
        'pools': [POOL_WETH_USDC],
        'max_repay': 150_000 * 10**6,
    },
}
AGG_TO_MARKET = {a: k for k, m in MARKETS.items() for a in m['aggs']}
T_ANSWER = '0x0559884fd3a460db3073b7fc896cc77986f16e378210ded43186175bf646fc5f'  # AnswerUpdated
T_OEV = '0x8d530b9ddc4b318d28fdd4c3a21fcfecece54c1a72a824f262985b99afef009b'  # update inside Atlas txs
T_LIQ = '0xa4946ede45d0c6f06a0f5ce92c9ad3b4751452d2fe0e25010783bcab57a67e41'  # Morpho Liquidate
SEL_TAKE = '0xfcffee47'      # take((address,address,address,address,uint256),address,uint256,address[],uint256)
SEL_POSITION = '0x93c52062'
SEL_MARKET = '0x5c60e39a'
SEL_PRICE = '0xa035b1fe'
SEL_TRYAGG = '0xbce38bd7'
PAPER_EXEC = '0xb464f7314d55ec6a9a0cf6f7f6df17af8ed5b352'   # fork deployment; paper code override only
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
SEED = json.loads((HERE / 'seed-borrowers.json').read_text())   # {'cbeth': [...], 'weth': [...]}

# ---- loss guard (trial rule: every send's gas cap < 1 USD) ----
GAS_LIMIT = 550_000            # fork: success 372,266, NoProfit revert 437,522 (two-hop route)
SEND_CAP_USD = 0.95            # gas cap + L1 allowance of one send must stay under this (< 1 USD)
ETH_MARGIN = 1.15              # ETH valued 15% above the on-chain ETH/USD read when sizing the cap
ETH_FALLBACK_USD = 4000.0      # used until the WETH market oracle has been read
ETH_MIN_USD = 1000.0           # an implausibly low read falls back to the high value
L1_FEE_USD = 0.03              # allowance for the OP-stack L1 data fee of a ~520-byte tx
BID_SHARE = 0.40               # priority fee bid is at most 40% of simulated gross
NEAR_COUNT = 200               # per market: one Multicall per check
FULL_SCAN_INTERVAL = 21600     # full scan every 6 h ...
FULL_SCAN_MIN_GAP = 1800       # ... or after a 1% oracle move, at most every 30 min
FULL_SCAN_MOVE = 0.01
SAFETY_POLL = 420
CU_COST = {'eth_call': 26, 'eth_getLogs': 75, 'eth_getTransactionReceipt': 20,
           'eth_blockNumber': 10, 'eth_gasPrice': 10}
CU_CAP = 70_000                # relay reads/day; the feed filter (~20k CU/day) is on top
_id = 0
_eth_usd = None


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


def read_batch(mk, users):
    """One eth_call: this market's oracle price and totals, the WETH market's oracle price
    (= ETH/USD, for the gas cap) and position() of each user.
    Returns (price, totalBorrowAssets, totalBorrowShares, [(borrowShares, collateral)])."""
    global _eth_usd
    m = MARKETS[mk]
    calls = [(m['oracle'], SEL_PRICE), (MORPHO, SEL_MARKET + m['id']), (MARKETS['weth']['oracle'], SEL_PRICE)]
    calls += [(MORPHO, SEL_POSITION + m['id'] + aw(u)) for u in users]
    res = try_aggregate(calls)
    if not res[0][0] or not res[1][0] or len(res[1][1]) < 2 + 6 * 64:
        raise RuntimeError('oracle or market read failed')
    price = at(res[0][1], 0)
    tba, tbs = at(res[1][1], 2), at(res[1][1], 3)
    if res[2][0] and len(res[2][1]) >= 66:
        # Morpho oracle price is scaled 1e36 * 1e6 (USDC) / 1e18 (WETH) = 1e24 per whole USD/ETH
        _eth_usd = at(res[2][1], 0) / 1e24
    pos = []
    for ok, data in res[3:]:
        if ok and len(data) >= 2 + 3 * 64:
            pos.append((at(data, 1), at(data, 2)))
        else:
            pos.append((0, 0))
    return price, tba, tbs, pos


def eth_ref_usd():
    """ETH price used to turn the fee cap into USD: on-chain read plus a margin, never a low guess."""
    if _eth_usd is None or _eth_usd < ETH_MIN_USD:
        return ETH_FALLBACK_USD
    return _eth_usd * ETH_MARGIN


def ratio(mk, shares, coll, price, tba, tbs):
    """debt / maxBorrow from stored totals (interest since lastUpdate not included). > 1 = liquidatable."""
    if shares == 0:
        return 0.0, 0
    debt = shares * (tba + 1) // (tbs + 10**6)
    max_borrow = coll * price // 10**36 * MARKETS[mk]['lltv'] // 10**18
    if max_borrow == 0:
        return 99.0, debt
    return debt / max_borrow, debt


def fresh_state():
    return {'near': {k: [] for k in MARKETS}, 'feed_cursor': None, 'last_full': {k: 0 for k in MARKETS},
            'last_poll': 0, 'cooldown': {}, 'full_price': {}, 'last_price': {},
            'seed_n': {k: len(SEED[k]) for k in MARKETS}}


def load_state():
    if STATE.exists():
        try:
            s = json.loads(STATE.read_text())
            if s.get('seed_n') == {k: len(SEED[k]) for k in MARKETS}:
                return s
        except Exception:
            pass
    return fresh_state()


def save_state(s):
    tmp = STATE.with_suffix('.tmp')
    tmp.write_text(json.dumps(s, separators=(',', ':')))
    tmp.replace(STATE)


def owner():
    sys.path.append('/opt/farm/lib')   # the live service does not put it on the path
    import farmbot_signer
    a = farmbot_signer.my_address()
    a = a['address'] if isinstance(a, dict) else a
    if not isinstance(a, str) or len(a) != 42:
        raise RuntimeError('signer my_address returned no address')
    return a


def calldata(mk, user, shares, min_profit):
    """take(mp, borrower, repaidShares, pools[], minProfit): 5 static mp words, then
    borrower, shares, offset of pools (9 head words = 0x120), minProfit, then the array."""
    m = MARKETS[mk]
    return (SEL_TAKE + aw(USDC) + aw(m['coll']) + aw(m['oracle']) + aw(IRM) + word(m['lltv'])
            + aw(user) + word(shares) + word(9 * 32) + word(min_profit)
            + word(len(m['pools'])) + ''.join(aw(p) for p in m['pools']))


def sim(mk, user, shares, min_profit, from_addr, exec_addr, code):
    tx = {'from': from_addr, 'to': exec_addr, 'data': calldata(mk, user, shares, min_profit), 'gas': hex(GAS_LIMIT)}
    params = [tx, 'latest'] + ([{exec_addr: {'code': code}}] if code else [])
    return at(rpc('eth_call', params), 0)


def winner_block(mk, user, send_block, our_hash):
    lo = max(0, send_block - 50)
    hi = max(send_block, int(rpc('eth_blockNumber', []), 16))
    logs = rpc('eth_getLogs', [{'address': MORPHO, 'fromBlock': hex(lo), 'toBlock': hex(hi),
                               'topics': [T_LIQ, '0x' + MARKETS[mk]['id'], None, '0x' + aw(user)]}])
    ours = [int(x['blockNumber'], 16) for x in logs if x['transactionHash'].lower() == our_hash.lower()]
    if ours:
        return min(ours)
    return min((int(x['blockNumber'], 16) for x in logs), default=None)


def send_live(mk, user, data, max_fee, priority, gross_usd):
    sys.path.append('/opt/farm/lib')
    import farmbot_signer
    reply = farmbot_signer.send(CHAIN, EXEC, data, 0, GAS_LIMIT, max_fee, max_priority_fee_per_gas=priority)
    h = reply.get('txHash') if isinstance(reply, dict) else None
    if not h:
        log('signer_reject', market=mk, user=user, reply=reply)  # final: no retry
        return
    receipt = None
    for _ in range(30):  # base blocks are 0.2 s; give up after 15 s
        time.sleep(0.5)
        receipt = rpc('eth_getTransactionReceipt', [h])
        if receipt:
            break
    if not receipt:
        log('send_result', hash=h, market=mk, user=user, result='unknown', gas_used=None, winner_block=None)
        return
    b = int(receipt['blockNumber'], 16)
    status = int(receipt['status'], 16)
    used = int(receipt['gasUsed'], 16)
    price = int(receipt['effectiveGasPrice'], 16)
    l1 = int(receipt.get('l1Fee') or '0x0', 16)
    try:
        winner = winner_block(mk, user, b, h)
    except Exception:
        winner = None
    log('send_result', hash=h, market=mk, user=user, result='won' if status else 'lost', gas_used=used,
        gas_cost_wei=used * price + l1, l1_fee_wei=l1, winner_block=winner, send_block=b,
        blocks_after_winner=(b - winner if winner is not None else None), gross_usd=gross_usd)


def attempt(s, mk, user, shares, debt, r, why):
    now = time.time()
    key = f'{mk}:{user}'
    if s['cooldown'].get(key, 0) > now:
        return
    s['cooldown'][key] = now + 600
    from_addr = owner() if MODE == 'live' else PAPER_OWNER
    exec_addr = EXEC if MODE == 'live' else PAPER_EXEC
    code = None if MODE == 'live' else RUNTIME
    cap = MARKETS[mk]['max_repay']
    # full debt, or the part under the size cap; one smaller retry if the route cannot absorb it
    sizes = [shares if debt <= cap else shares * cap // debt]
    sizes.append(sizes[0] // 8)
    for size in sizes:
        if size == 0:
            continue
        try:
            gain = sim(mk, user, size, 1, from_addr, exec_addr, code)
        except ReadBudgetExceeded:
            raise
        except Exception as e:
            log('simulate_revert', market=mk, user=user, why=why, ratio=r, shares=size, error=str(e)[:200])
            if 'healthy' in str(e):
                s['cooldown'][key] = now + 20       # borderline: look again on the next update
                return
            s['cooldown'][key] = now + 21600        # unsellable / bad debt: do not burn reads on it
            continue
        gross_usd = gain / 1e6
        eth_usd = eth_ref_usd()
        base_fee = int(rpc('eth_gasPrice', []), 16)
        # hard fee cap: GAS_LIMIT x maxFeePerGas valued at eth_usd, plus the L1 allowance, < SEND_CAP_USD
        fee_cap = int((SEND_CAP_USD - L1_FEE_USD) / eth_usd * 1e18 / GAS_LIMIT)
        priority = int(gross_usd * BID_SHARE / eth_usd * 1e18 / GAS_LIMIT)
        max_fee = min(fee_cap, base_fee * 2 + priority)
        priority = min(priority, max_fee)
        gas_cap_usd = GAS_LIMIT * max_fee / 1e18 * eth_usd + L1_FEE_USD
        if max_fee < base_fee or gas_cap_usd >= 1.0 or gross_usd <= gas_cap_usd:
            log('opportunity_skip', market=mk, user=user, why=why, ratio=r, gross_usd=gross_usd,
                gas_cap_usd=gas_cap_usd, base_fee=base_fee, eth_usd=eth_usd, reason='gross_not_above_gas_cap')
            return
        min_profit = int(gas_cap_usd * 1e6)
        data = calldata(mk, user, size, min_profit)
        try:
            gain = sim(mk, user, size, min_profit, from_addr, exec_addr, code)  # the exact bytes to send
        except ReadBudgetExceeded:
            raise
        except Exception as e:
            log('simulate_revert', market=mk, user=user, why=why, ratio=r, shares=size, error=str(e)[:200])
            return
        log('opportunity', market=mk, user=user, why=why, ratio=r, shares=size, debt_usdc=debt / 1e6,
            gross_usd=gross_usd, gas_cap_usd=gas_cap_usd, max_fee=max_fee, priority=priority,
            eth_usd=eth_usd, simulated_gain=gain, mode=MODE)
        if MODE == 'live':
            send_live(mk, user, data, max_fee, priority, gross_usd)
        else:
            log('paper_sim', market=mk, user=user, result='success', gain=gain)
        return


def scan(s, mk, users, label):
    rows = []
    price = None
    for off in range(0, len(users), 200):
        batch = users[off:off + 200]
        try:
            price, tba, tbs, pos = read_batch(mk, batch)
        except ReadBudgetExceeded:
            raise
        except Exception as e:
            log('scan_error', market=mk, label=label, offset=off, error=str(e)[:200])
            continue
        for u, (shares, coll) in zip(batch, pos):
            if shares > 0:
                r, debt = ratio(mk, shares, coll, price, tba, tbs)
                rows.append((r, u, shares, debt))
    if label == 'full':
        near = sorted(rows, key=lambda z: abs(z[0] - 1.0))[:NEAR_COUNT]
        s['near'][mk] = [u for _, u, _, _ in near]
        if price:
            s['full_price'][mk] = str(price)
    if price:
        s['last_price'][mk] = str(price)
    # stored totals lag accrued interest slightly: simulate everything from 0.9998 up
    cands = sorted([z for z in rows if 0.9998 <= z[0] < 50], key=lambda z: -z[3])
    log('scan', market=mk, label=label, checked=len(users), debtors=len(rows), candidates=len(cands),
        near=len(s['near'][mk]), top_ratio=max((z[0] for z in rows if z[0] < 50), default=None))
    for r, u, shares, debt in cands[:5]:
        attempt(s, mk, u, shares, debt, r, label)


def full_scan_due(s, mk, now):
    if not s['near'][mk] or now - s['last_full'][mk] >= FULL_SCAN_INTERVAL:
        return True
    try:
        moved = abs(int(s['last_price'][mk]) / int(s['full_price'][mk]) - 1.0)
    except Exception:
        return False
    return moved >= FULL_SCAN_MOVE and now - s['last_full'][mk] >= FULL_SCAN_MIN_GAP


def scan_near(s, label, markets=None):
    for mk in (markets or list(MARKETS)):
        scan(s, mk, s['near'][mk], label)
    s['last_poll'] = time.time()


def feed_wait(cursor):
    q = {'address': ','.join(sorted(AGG_TO_MARKET)), 'topic0': f'{T_ANSWER},{T_OEV}', 'timeout': '55'}
    if cursor:
        q['after'] = cursor
    with urllib.request.urlopen(f'{FEED}/logs/{CHAIN}?' + urllib.parse.urlencode(q), timeout=65) as r:
        return json.load(r)


def main():
    s = load_state()
    log('start', mode=MODE, executor=EXEC if MODE == 'live' else PAPER_EXEC, seed={k: len(v) for k, v in SEED.items()}, near={k: len(v) for k, v in s['near'].items()})
    while True:
        now = time.time()
        try:
            did_full = False
            for mk in MARKETS:
                if full_scan_due(s, mk, now):
                    scan(s, mk, SEED[mk], 'full')
                    s['last_full'][mk] = now
                    did_full = True
            if did_full:
                s['last_poll'] = time.time()
            elif now - s['last_poll'] >= SAFETY_POLL:
                scan_near(s, 'safety_poll')
            s['cooldown'] = {u: t for u, t in s['cooldown'].items() if t > now}
            save_state(s)
            result = feed_wait(s.get('feed_cursor'))
            s['feed_cursor'] = result.get('cursor', s.get('feed_cursor'))
            if result.get('gap') or any(x.get('removed') for x in result.get('logs', [])):
                scan_near(s, 'gap')
            elif result.get('logs'):
                hit = sorted({AGG_TO_MARKET[x['address'].lower()] for x in result['logs']
                              if x.get('address', '').lower() in AGG_TO_MARKET}) or list(MARKETS)
                log('feed', events=len(result['logs']), markets=hit,
                    blocks=sorted({int(x['blockNumber'], 16) for x in result['logs']}),
                    topics=sorted({x['topics'][0][:10] for x in result['logs']}))
                for mk in hit:
                    scan(s, mk, s['near'][mk], 'oracle_update')
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
            log('feed_error', error=str(e)[:180])
            try:
                scan_near(s, 'gap')
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
