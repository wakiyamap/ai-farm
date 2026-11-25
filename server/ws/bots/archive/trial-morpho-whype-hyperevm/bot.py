#!/usr/bin/env python3
"""Trial: Morpho Blue WHYPE/USDC liquidations on HyperEVM through the TrialMorphoHyperTake
executor (direct Morpho liquidate, no auctioneer wrapper).

Timer bot: every POLL_S seconds one Multicall3 read (oracle prices, market totals and the
positions nearest the threshold). A position over the line is simulated through the executor
and (live) sent. A lost attempt costs gas only (executor NoProfit guard).
"""
import datetime
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
MODE = os.environ.get('BOT_MODE', 'paper')
LANE = os.environ.get('RPC_LANE', 'paper')
RELAY = os.environ['RPC_RELAY_URL'].rstrip('/')
CHAIN = 'hyperevm'
MORPHO = '0x68e37de8d93d3496ae143f2e900490f6280c57cd'
USDC = '0xb88339cb7199b77e23db6e890353e22632ba630f'
WHYPE = '0x5555555555555555555555555555555555555555'
IRM = '0xd4a426f010986dcad727e8dd6eed44ca4a9b7483'
MULTICALL = '0xca11bde05977b3631167028862be2a173976ca11'
POOL_WHYPE_USDC = '0x6c9a33e3b592c0d65b3ba59355d5be0d38259285'   # UniV3-style 0.05%, token0 WHYPE, token1 USDC
ORACLE_A = '0x194fff37872bac3531a41fa5c426090ff84f4f31'
ORACLE_B = '0xa6ecdf8cb132bfa50916a421d06be41a57179dd9'
# Markets are data (idToMarketParams read 2026-11-17): id, oracle, lltv, sale route, size cap.
MARKETS = {
    'whype77': {
        'id': 'd7d38220652d19c87099c3b23de9a70a1893620a050c635d1a94bd947c9c59a8',
        'coll': WHYPE, 'oracle': ORACLE_A, 'lltv': 770000000000000000,
        'pools': [POOL_WHYPE_USDC], 'max_repay': 100_000 * 10**6,
    },
    'whype62': {
        'id': 'd13b1bad542045a8dc729fa0ffcc4f538b9771592c2666e1f09667dcf85804fc',
        'coll': WHYPE, 'oracle': ORACLE_A, 'lltv': 625000000000000000,
        'pools': [POOL_WHYPE_USDC], 'max_repay': 100_000 * 10**6,
    },
    'whype86': {
        'id': 'f1c3d487f417d00952e037e551fa01ec663092139d90e31fc901b3cd83f84ebb',
        'coll': WHYPE, 'oracle': ORACLE_B, 'lltv': 860000000000000000,
        'pools': [POOL_WHYPE_USDC], 'max_repay': 100_000 * 10**6,
    },
}
ID_TO_MARKET = {m['id']: k for k, m in MARKETS.items()}
T_LIQ = '0xa4946ede45d0c6f06a0f5ce92c9ad3b4751452d2fe0e25010783bcab57a67e41'     # Morpho Liquidate
T_BORROW = '0x570954540bed6b1304a87dfe815a5eda4a648f7097a16240dcd85c9b5fd42a43'  # Morpho Borrow
SEL_TAKE = '0x6b5e5316'      # take((address,address,address,address,uint256),address,uint256,uint256,address[],uint256)
SEL_POSITION = '0x93c52062'
SEL_MARKET = '0x5c60e39a'
SEL_PRICE = '0xa035b1fe'
SEL_TRYAGG = '0xbce38bd7'
PAPER_EXEC = '0x3fd20887f5d593ed88b9977dec8a9f12bf05cf6a'   # fork deployment; paper code override only
PAPER_OWNER = '0xc0ffee0000000000000000000000000000002281'  # the owner baked into that deployment
EXEC = os.environ.get('EXECUTOR_ADDR_HYPEREVM') or os.environ.get('EXECUTOR_ADDR')
if MODE == 'live' and not EXEC:
    raise SystemExit('EXECUTOR_ADDR_HYPEREVM or EXECUTOR_ADDR is required in live mode')
RUNTIME = (HERE / 'executor-runtime.hex').read_text().strip()
if not RUNTIME.startswith('0x'):
    raise SystemExit('missing paper executor runtime')
LOG = HERE / 'logs' / 'bot.jsonl'
STATE = HERE / 'state' / 'state.json'
CU_FILE = HERE / 'state' / 'cu.json'
LOG.parent.mkdir(exist_ok=True)
STATE.parent.mkdir(exist_ok=True)
SEED = json.loads((HERE / 'seed-borrowers.json').read_text())   # {'block': n, 'whype77': [...], ...}

# ---- loss guard (trial rule: every send's gas cap < 1 USD) ----
GAS_LIMIT = 450_000            # fork: success 292,981, NoProfit revert 338,426; chain cap 2,000,000
SEND_CAP_USD = 0.95            # GAS_LIMIT x maxFeePerGas of one send stays under this (< 1 USD)
HYPE_MARGIN = 1.15             # HYPE valued 15% above the on-chain oracle read when sizing the cap
HYPE_FALLBACK_USD = 200.0      # used until the oracle has been read
HYPE_MIN_USD = 10.0            # an implausibly low read falls back to the high value
BID_SHARE = 0.40               # priority fee bid is at most 40% of simulated gross
POLL_S = 60                    # timer: one Multicall per poll
FAST_POLL_S = 6                # while a sizable position is within 1.5% of the line (measured windows: 3-9 blocks of ~1 s)
FAST_RATIO = 0.985
FAST_MIN_DEBT = 20 * 10**6     # USDC (6 dp): smaller positions do not switch the fast timer on
SLOW_CU_PER_S = 0.6            # reserve for the slow timer (about 52k CU/day) when allowing fast polls
NEAR_RATIO = 0.85              # positions at or above this debt/maxBorrow are read on every poll
NEAR_MAX = 150
FULL_SCAN_INTERVAL = 1800      # all known borrowers every 30 min (3 Multicalls)
DISCOVER_INTERVAL = 1800       # new borrowers from Morpho Borrow logs every 30 min (1 getLogs)
DISCOVER_MAX_BLOCKS = 5000
CU_COST = {'eth_call': 26, 'eth_getLogs': 75, 'eth_getTransactionReceipt': 20,
           'eth_blockNumber': 10, 'eth_gasPrice': 10}
CU_CAP = 90_000                # relay CU/day, hard cap in code (trial rule: <= 100,000)
_id = 0
_hype_usd = None


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


def try_aggregate(calls, block='latest'):
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
    h = rpc('eth_call', [{'to': MULTICALL, 'data': enc}, block])[2:]
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


def read_batch(pairs, block='latest'):
    """One eth_call: both oracles' price(), market() of the three markets and position() of each
    (market key, user) pair. Returns ({mk: (price, totalBorrowAssets, totalBorrowShares)},
    [(borrowShares, collateral)])."""
    global _hype_usd
    keys = list(MARKETS)
    calls = [(ORACLE_A, SEL_PRICE), (ORACLE_B, SEL_PRICE)]
    calls += [(MORPHO, SEL_MARKET + MARKETS[k]['id']) for k in keys]
    calls += [(MORPHO, SEL_POSITION + MARKETS[mk]['id'] + aw(u)) for mk, u in pairs]
    res = try_aggregate(calls, block)
    prices = {}
    for i, o in enumerate((ORACLE_A, ORACLE_B)):
        if res[i][0] and len(res[i][1]) >= 66:
            prices[o] = at(res[i][1], 0)
    if ORACLE_A in prices:
        # Morpho oracle price is scaled 1e36 * 1e6 (USDC) / 1e18 (WHYPE) = 1e24 per whole USD/HYPE
        _hype_usd = prices[ORACLE_A] / 1e24
    mkt = {}
    for i, k in enumerate(keys):
        ok, data = res[2 + i]
        price = prices.get(MARKETS[k]['oracle'])
        if ok and len(data) >= 2 + 6 * 64 and price:
            mkt[k] = (price, at(data, 2), at(data, 3))
    pos = []
    for ok, data in res[2 + len(keys):]:
        if ok and len(data) >= 2 + 3 * 64:
            pos.append((at(data, 1), at(data, 2)))
        else:
            pos.append((0, 0))
    return mkt, pos


def hype_ref_usd():
    """HYPE price used to turn the fee cap into USD: on-chain read plus a margin, never a low guess."""
    if _hype_usd is None or _hype_usd < HYPE_MIN_USD:
        return HYPE_FALLBACK_USD
    return _hype_usd * HYPE_MARGIN


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
    return {'users': {k: list(SEED[k]) for k in MARKETS}, 'near': [], 'last_full': 0, 'last_discover': 0,
            'discover_block': int(SEED['block']), 'cooldown': {}, 'seed_block': int(SEED['block'])}


def load_state():
    if STATE.exists():
        try:
            s = json.loads(STATE.read_text())
            if s.get('seed_block') == int(SEED['block']):
                return s
        except Exception:
            pass
    return fresh_state()


def save_state(s):
    tmp = STATE.with_suffix('.tmp')
    tmp.write_text(json.dumps(s, separators=(',', ':')))
    tmp.replace(STATE)


def signer():
    sys.path.append('/opt/farm/lib')
    import farmbot_signer
    return farmbot_signer


def owner():
    a = signer().my_address()
    a = a['address'] if isinstance(a, dict) else a
    if not isinstance(a, str) or len(a) != 42:
        raise RuntimeError('signer my_address returned no address')
    return a


def calldata(mk, user, seized, shares, min_profit):
    """take(mp, borrower, seizedAssets, repaidShares, pools[], minProfit): 5 static mp words, then
    borrower, seized, shares, offset of pools (10 head words = 0x140), minProfit, then the array."""
    m = MARKETS[mk]
    return (SEL_TAKE + aw(USDC) + aw(m['coll']) + aw(m['oracle']) + aw(IRM) + word(m['lltv'])
            + aw(user) + word(seized) + word(shares) + word(10 * 32) + word(min_profit)
            + word(len(m['pools'])) + ''.join(aw(p) for p in m['pools']))


def sim(mk, user, seized, shares, min_profit, from_addr, exec_addr, code, block='latest'):
    tx = {'from': from_addr, 'to': exec_addr, 'data': calldata(mk, user, seized, shares, min_profit),
          'gas': hex(GAS_LIMIT)}
    params = [tx, block] + ([{exec_addr: {'code': code}}] if code else [])
    return at(rpc('eth_call', params), 0)


def winner_block(mk, user, send_block, our_hash):
    lo = max(0, send_block - 300)
    hi = max(send_block, int(rpc('eth_blockNumber', []), 16))
    logs = rpc('eth_getLogs', [{'address': MORPHO, 'fromBlock': hex(lo), 'toBlock': hex(hi),
                               'topics': [T_LIQ, '0x' + MARKETS[mk]['id'], None, '0x' + aw(user)]}])
    ours = [int(x['blockNumber'], 16) for x in logs if x['transactionHash'].lower() == our_hash.lower()]
    if ours:
        return min(ours)
    return min((int(x['blockNumber'], 16) for x in logs), default=None)


def send_live(mk, user, data, max_fee, priority, gross_usd):
    reply = signer().send(CHAIN, EXEC, data, 0, GAS_LIMIT, max_fee, max_priority_fee_per_gas=priority)
    h = reply.get('txHash') if isinstance(reply, dict) else None
    if not h:
        log('signer_reject', market=mk, user=user, reply=reply)  # final: no retry
        return
    receipt = None
    for _ in range(25):  # ~1 s blocks; give up after 25 s
        time.sleep(1.0)
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
    try:
        winner = winner_block(mk, user, b, h)
    except Exception:
        winner = None
    log('send_result', hash=h, market=mk, user=user, result='won' if status else 'lost', gas_used=used,
        gas_cost_wei=used * price, winner_block=winner, send_block=b,
        blocks_after_winner=(b - winner if winner is not None else None), gross_usd=gross_usd)


def attempt(s, mk, user, shares, coll, debt, r, why):
    now = time.time()
    key = f'{mk}:{user}'
    if s['cooldown'].get(key, 0) > now:
        return
    seen = s.get('healthy_at', {}).get(key)
    if seen and r <= seen[0] + 1e-6 and now - seen[1] < 600:
        return
    s['cooldown'][key] = now + 600
    from_addr = owner() if MODE == 'live' else PAPER_OWNER
    exec_addr = EXEC if MODE == 'live' else PAPER_EXEC
    code = None if MODE == 'live' else RUNTIME
    cap = MARKETS[mk]['max_repay']
    # (seizedAssets, repaidShares): the full debt (or the part under the size cap); then all the
    # collateral (a position whose collateral no longer covers the full debt); then an eighth.
    first = shares if debt <= cap else shares * cap // debt
    sizes = [(0, first), (coll, 0) if debt <= cap else (0, 0), (0, first // 8)]
    for seized, size in sizes:
        if seized == 0 and size == 0:
            continue
        try:
            gain = sim(mk, user, seized, size, 1, from_addr, exec_addr, code)
        except ReadBudgetExceeded:
            raise
        except Exception as e:
            log('simulate_revert', market=mk, user=user, why=why, ratio=r, seized=seized, shares=size,
                error=str(e)[:200])
            if 'healthy' in str(e):
                # borderline (stored totals lag interest): simulate again when the ratio has
                # risen, or after 10 min
                s['cooldown'].pop(key, None)
                s.setdefault('healthy_at', {})[key] = [r, now]
                return
            s['cooldown'][key] = now + 3600         # unsellable / bad debt: do not burn reads on it
            continue
        gross_usd = gain / 1e6
        hype_usd = hype_ref_usd()
        base_fee = int(rpc('eth_gasPrice', []), 16)
        # hard fee cap: GAS_LIMIT x maxFeePerGas valued at hype_usd stays under SEND_CAP_USD
        fee_cap = int(SEND_CAP_USD / hype_usd * 1e18 / GAS_LIMIT)
        priority = int(gross_usd * BID_SHARE / hype_usd * 1e18 / GAS_LIMIT)
        max_fee = min(fee_cap, base_fee * 2 + priority)
        priority = min(priority, max_fee)
        gas_cap_usd = GAS_LIMIT * max_fee / 1e18 * hype_usd
        if max_fee < base_fee or gas_cap_usd >= 1.0 or gross_usd <= gas_cap_usd:
            log('opportunity_skip', market=mk, user=user, why=why, ratio=r, gross_usd=gross_usd,
                gas_cap_usd=gas_cap_usd, base_fee=base_fee, fee_cap=fee_cap, hype_usd=hype_usd,
                reason='base_fee_above_fee_cap' if max_fee < base_fee else 'gross_not_above_gas_cap')
            s['cooldown'][key] = now + 60
            return
        min_profit = max(1, int(gas_cap_usd * 1e6))
        data = calldata(mk, user, seized, size, min_profit)
        try:
            gain = sim(mk, user, seized, size, min_profit, from_addr, exec_addr, code)  # the exact bytes to send
        except ReadBudgetExceeded:
            raise
        except Exception as e:
            log('simulate_revert', market=mk, user=user, why=why, ratio=r, seized=seized, shares=size,
                error=str(e)[:200])
            return
        log('opportunity', market=mk, user=user, why=why, ratio=r, seized=seized, shares=size,
            debt_usdc=debt / 1e6, gross_usd=gross_usd, gas_cap_usd=gas_cap_usd, max_fee=max_fee,
            priority=priority, hype_usd=hype_usd, simulated_gain=gain, mode=MODE)
        if MODE == 'live':
            send_live(mk, user, data, max_fee, priority, gross_usd)
        else:
            log('paper_sim', market=mk, user=user, result='success', gain=gain)
        return


def scan(s, pairs, label):
    rows = []
    for off in range(0, len(pairs), 150):
        batch = pairs[off:off + 150]
        try:
            mkt, pos = read_batch(batch)
        except ReadBudgetExceeded:
            raise
        except Exception as e:
            log('scan_error', label=label, offset=off, error=str(e)[:200])
            continue
        for (mk, u), (shares, coll) in zip(batch, pos):
            if shares > 0 and mk in mkt:
                price, tba, tbs = mkt[mk]
                r, debt = ratio(mk, shares, coll, price, tba, tbs)
                rows.append((r, mk, u, shares, coll, debt))
    if label == 'full':
        near = sorted([z for z in rows if z[0] >= NEAR_RATIO], key=lambda z: -z[0])[:NEAR_MAX]
        s['near'] = [[mk, u] for _, mk, u, _, _, _ in near]
    # stored totals lag accrued interest slightly: simulate everything from 0.9995 up
    cands = sorted([z for z in rows if 0.9995 <= z[0] < 50], key=lambda z: -z[5])
    log('scan', label=label, checked=len(pairs), debtors=len(rows), candidates=len(cands), near=len(s['near']),
        top_ratio=max((z[0] for z in rows if z[0] < 50), default=None), hype_usd=_hype_usd)
    for r, mk, u, shares, coll, debt in cands[:5]:
        attempt(s, mk, u, shares, coll, debt, r, label)
    return any(z[0] >= FAST_RATIO and z[5] >= FAST_MIN_DEBT for z in rows if z[0] < 50)


def fast_allowed():
    """Fast polls only while today's CU plus the slow timer's need for the rest of the day fits the cap."""
    now = datetime.datetime.now(datetime.timezone.utc)
    left = 86400 - (now.hour * 3600 + now.minute * 60 + now.second)
    try:
        budget = json.loads(CU_FILE.read_text())
        used = budget['cu'] if budget.get('day') == now.date().isoformat() else 0
    except Exception:
        used = 0
    return used + SLOW_CU_PER_S * left <= CU_CAP


def discover(s):
    """New borrowers of the three markets from Morpho Borrow logs (onBehalf = topic 2)."""
    head = int(rpc('eth_blockNumber', []), 16)
    lo = s['discover_block'] + 1
    if head - lo > DISCOVER_MAX_BLOCKS:
        log('discover_gap', skipped_from=lo, skipped_to=head - DISCOVER_MAX_BLOCKS)
        lo = head - DISCOVER_MAX_BLOCKS
    if lo > head:
        return
    logs = rpc('eth_getLogs', [{'address': MORPHO, 'fromBlock': hex(lo), 'toBlock': hex(head),
                               'topics': [T_BORROW, ['0x' + m['id'] for m in MARKETS.values()]]}])
    added = 0
    for x in logs:
        mk = ID_TO_MARKET.get(x['topics'][1][2:].lower())
        u = '0x' + x['topics'][2][-40:].lower()
        if mk and u not in s['users'][mk]:
            s['users'][mk].append(u)
            added += 1
    s['discover_block'] = head
    log('discover', from_block=lo, to_block=head, borrow_logs=len(logs), added=added,
        users={k: len(v) for k, v in s['users'].items()})


def main():
    s = load_state()
    log('start', mode=MODE, executor=EXEC if MODE == 'live' else PAPER_EXEC,
        users={k: len(v) for k, v in s['users'].items()}, near=len(s['near']), poll_s=POLL_S)
    while True:
        now = time.time()
        hot = False
        try:
            if now - s['last_discover'] >= DISCOVER_INTERVAL:
                s['last_discover'] = now
                discover(s)
            if now - s['last_full'] >= FULL_SCAN_INTERVAL:
                s['last_full'] = now
                hot = scan(s, [(mk, u) for mk in MARKETS for u in s['users'][mk]], 'full')
            else:
                hot = scan(s, [tuple(p) for p in s['near']], 'poll')
            s['cooldown'] = {u: t for u, t in s['cooldown'].items() if t > now}
            s['healthy_at'] = {u: v for u, v in s.get('healthy_at', {}).items() if now - v[1] < 600}
        except ReadBudgetExceeded as e:
            log('read_budget', error=str(e))
            save_state(s)
            time.sleep(600)
            continue
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
            log('relay_error', error=str(e)[:180])
        except Exception as e:
            log('loop_error', error=str(e)[:250])
        save_state(s)
        fast = bool(hot) and fast_allowed()
        if fast != s.get('fast', False):
            log('timer', fast=fast, poll_s=FAST_POLL_S if fast else POLL_S)
            s['fast'] = fast
        time.sleep(max(1.0, (FAST_POLL_S if fast else POLL_S) - (time.time() - now)))


if __name__ == '__main__':
    main()
