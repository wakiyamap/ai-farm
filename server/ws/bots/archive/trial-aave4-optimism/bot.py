#!/usr/bin/env python3
"""Trial: Aave V4 liquidations on the EtherFi borrowing market spoke (OP Mainnet) through the
TrialAave4TakeOp executor.

Scope: USDC debt (reserve 0) against USDC, WETH or USDT collateral (reserves 0, 1, 2). The bot keeps
the borrowers nearest the threshold, waits on the farm feed for AnswerUpdated of the Chainlink
aggregators behind the spoke oracle (ETH / USD, USDC / USD, USDT / USD), re-reads their health factor
with one Multicall3 read when a price changed (plus a 5-minute safety poll), simulates the executor call (Morpho flash
loan -> liquidationCall -> sell the collateral on UniV3 pools -> repay) and, live, sends it.
A lost attempt costs gas only (executor NoProfit guard).
"""
import sys as _farm_sys; _farm_sys.path.append("/opt/farm/lib")  # signer import path for the live service
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
CHAIN = 'optimism'
SPOKE = '0xdffcc3536d932eb51df51a7f5fa407c4270d5308'
ORACLE = '0xe8cbd37210bf1e29436dae183d7b9fe45e886fa8'   # spoke.ORACLE()
USDC = '0x0b2c639c533813f4aa9d7837caf62653d097ff85'
WETH = '0x4200000000000000000000000000000000000006'
USDT = '0x94b008aa00579c1307b0ef2c499ad98a8ce58e58'
MORPHO = '0xce95afbb8ea029495c66020883f87aae8864af92'   # Morpho Blue on OP Mainnet: zero-fee flashLoan
DEBT_RESERVE = 0                                         # USDC
MULTICALL = '0xca11bde05977b3631167028862be2a173976ca11'
# collateral reserves in scope: id -> (symbol, underlying, [pool paths to USDC, tried in order])
RESERVES = {
    0: ('USDC', USDC, [[]]),                                             # collateral is the debt token: no swap
    1: ('WETH', WETH, [['0x1fb3cf6e48f1e7b10213e7b6d87d4c073c7fdb7b']]),  # UniV3 WETH/USDC
    2: ('USDT', USDT, [['0x84ce89b4f6f67e523a81a82f9f2f14d84b726f6b']]),  # UniV3-style USDT/USDC
}
FEED = os.environ.get('FEED_URL', 'http://127.0.0.1:8546')
# The trigger. Health factors move when the spoke oracle's prices move, and those change only when the
# Chainlink aggregator behind each reserve's source emits AnswerUpdated (traced 2026-11-19,
# scratch/trial-aave4-optimism/trigger.py): source -> rateFeed() proxy -> aggregator()
AGGS = ['0x16c04812fa9db1d0236c3841dda8e86225bc3f3e',   # ETH / USD (reserve 1 source 0x4060f7d7..., proxy 0x13e3ee69...): ~480 updates/day
        '0xdb5a1d830b72ce47b881c0093dbc9c6321091e78',   # USDC / USD (reserve 0, capped adapter 0x5b057985..., proxy 0x16a9fa2f...): ~1/day
        '0xfd7f8e6ba7b6d36f4b3c9013de5fa527d8347643']   # USDT / USD (reserve 2, capped adapter 0x75799776..., proxy 0xecef79e1...): ~1/day
T_ANSWER = '0x0559884fd3a460db3073b7fc896cc77986f16e378210ded43186175bf646fc5f'  # AnswerUpdated(int256,uint256,uint256)
T_LIQ ='0x2a1f12d996f530f89d8038aa293f9fde81cac44b6dfd6225e3358d09b78a4a37'     # spoke LiquidationCall
T_BORROW = '0xef18174796a5d2f91d51dc5e907a4d7867bbd6e800f6225168e0453d581d0dcd'  # spoke Borrow
SEL_TAKE = '0x4f2c0eaa'      # take((address,address,address,uint256,uint256,address,address,uint256,address[]),uint256)
SEL_ACCOUNT = '0xbf92857c'     # getUserAccountData(address)
SEL_SUPPLIED = '0xf1568a89'    # getUserSuppliedAssets(uint256,address)
SEL_DEBT = '0x9b7172a6'        # getUserTotalDebt(uint256,address)
SEL_PRICE = '0xd45c35ff'       # oracle getReservePrice(uint256)
SEL_TRYAGG = '0xbce38bd7'
ERR_HEALTHY = 'e2fadb09'       # the spoke's "health factor not below threshold" revert on this deployment
PAPER_EXEC = '0xb464f7314d55ec6a9a0cf6f7f6df17af8ed5b352'
PAPER_OWNER = '0xc0ffee0000000000000000000000000000000001'
EXEC = os.environ.get('EXECUTOR_ADDR_OPTIMISM') or os.environ.get('EXECUTOR_ADDR')
if MODE == 'live' and not EXEC:
    raise SystemExit('EXECUTOR_ADDR_OPTIMISM or EXECUTOR_ADDR is required in live mode')
RUNTIME = (HERE / 'executor-runtime.hex').read_text().strip()
if not RUNTIME.startswith('0x'):
    raise SystemExit('missing paper executor runtime')
LOG = HERE / 'logs' / 'bot.jsonl'
STATE = HERE / 'state' / 'state.json'
CU_FILE = HERE / 'state' / 'cu.json'
LOG.parent.mkdir(exist_ok=True)
STATE.parent.mkdir(exist_ok=True)
SEED = json.loads((HERE / 'seed-borrowers.json').read_text())   # {"head": block, "users": [..]}
BLOCK_TAG = 'latest'           # changed only by the offline self-test

# ---- loss guard (trial rule: every send's gas cap < 1 USD) ----
GAS_LIMIT = 1_300_000          # fork: WETH success 947,868, NoProfit revert 1,046,300, USDC path 704,214
MAX_FEE_WEI = 150_000_000      # 0.15 gwei hard cap: 1.3M x 0.15 gwei = 1.95e-4 ETH
ETH_REF_USD = 4000.0           # deliberately high ETH price: cap = 0.78 USD at 4000 (0.35 at 1,800)
L1_FEE_USD = 0.02              # allowance for the OP-stack L1 data fee of a ~500-byte tx
BID_SHARE = 0.25               # priority fee bid is at most 25% of simulated gross
MAX_COVER_USDC = 20_000 * 10**6    # flash size cap per take; larger debts are taken in part
NEAR_MAX = 100                 # the 100 lowest health factors are re-read on every poll (one eth_call)
MIN_DEBT_VALUE = 2 * 10**52    # ignore debtors under 0.2 USD of debt (word 4 = USD x 1e53: 8,625.77 USDC reads 8.62e56)
BATCH = 100
FULL_SCAN_INTERVAL = 43200     # every borrower + new Borrow logs every 12 h
SAFETY_POLL = 300              # near set re-read when the feed has been silent this long (feed rule: 5-10 min)
FEED_DOWN_POLL = 60            # near set re-read at most this often while the feed answers 429 / 503 / errors
LOG_PAGE = 40_000              # Borrow logs: about 94 per 1,000 blocks
CU_COST = {'eth_call': 26, 'eth_getLogs': 75, 'eth_getTransactionReceipt': 20,
           'eth_blockNumber': 10, 'eth_gasPrice': 10}
CU_CAP = 75_000                # relay reads/day, hard cap in code; the feed filter (~15-20k CU/day) is on top
_id = 0


class ReadBudgetExceeded(Exception):
    pass


def log(ev, **kw):
    row = {'ts': time.time(), 'ev': ev, **kw}
    with LOG.open('a') as f:
        f.write(json.dumps(row, separators=(',', ':'), default=str) + '\n')


def _budget():
    day = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    try:
        budget = json.loads(CU_FILE.read_text())
    except Exception:
        budget = {}
    if budget.get('day') != day:
        budget = {'day': day, 'cu': 0, 'fast': 0}
    return budget


def rpc(method, params):
    global _id
    budget = _budget()
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
    h = rpc('eth_call', [{'to': MULTICALL, 'data': enc}, BLOCK_TAG])[2:]
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


def read_health(users):
    """One eth_call per BATCH users: getUserAccountData. Returns [(user, healthFactor, debtValue)]
    for users with debt (word 2 = healthFactor, word 4 = total debt value, word 6 = borrowCount)."""
    rows = []
    for off in range(0, len(users), BATCH):
        batch = users[off:off + BATCH]
        res = try_aggregate([(SPOKE, SEL_ACCOUNT + aw(u)) for u in batch])
        for u, (ok, data) in zip(batch, res):
            if ok and len(data) >= 2 + 7 * 64 and at(data, 6) > 0:
                rows.append((u, at(data, 2), at(data, 4)))
    return rows


def position(user):
    """One eth_call: the user's USDC debt and, per in-scope collateral reserve, supplied assets x oracle
    price. Returns (debt in USDC units, [(value, reserveId)] largest first)."""
    ids = sorted(RESERVES)
    calls = [(SPOKE, SEL_DEBT + word(DEBT_RESERVE) + aw(user))]
    calls += [(SPOKE, SEL_SUPPLIED + word(i) + aw(user)) for i in ids]
    calls += [(ORACLE, SEL_PRICE + word(i)) for i in ids]
    res = try_aggregate(calls)
    if not res[0][0] or len(res[0][1]) < 66:
        raise RuntimeError('debt read failed')
    debt = at(res[0][1], 0)
    vals = []
    for k, i in enumerate(ids):
        s_ok, s_data = res[1 + k]
        p_ok, p_data = res[1 + len(ids) + k]
        if s_ok and p_ok and len(s_data) >= 66 and len(p_data) >= 66 and at(s_data, 0) > 0:
            dec = 18 if i == 1 else 6
            vals.append((at(s_data, 0) * at(p_data, 0) // 10**dec, i))
    return debt, sorted(vals, reverse=True)


def load_state():
    if STATE.exists():
        try:
            s = json.loads(STATE.read_text())
            if s.get('seed_head') == SEED['head']:
                return s
        except Exception:
            pass
    return {'users': list(SEED['users']), 'scanned_to': SEED['head'], 'seed_head': SEED['head'],
            'near': [], 'near_min_hf': 0, 'last_full': 0, 'last_poll': 0, 'cooldown': {}}


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


def calldata(reserve, user, cover, path, min_profit):
    """take(Take, minProfit): Take is a dynamic tuple (it ends with address[] pools)."""
    token = RESERVES[reserve][1]
    tup = (aw(MORPHO) + aw(USDC) + aw(SPOKE) + word(reserve) + word(DEBT_RESERVE) + aw(token) + aw(user)
           + word(cover) + word(9 * 32) + word(len(path)) + ''.join(aw(p) for p in path))
    return SEL_TAKE + word(64) + word(min_profit) + tup


def sim(data, from_addr, exec_addr, code):
    tx = {'from': from_addr, 'to': exec_addr, 'data': data, 'gas': hex(GAS_LIMIT)}
    params = [tx, BLOCK_TAG] + ([{exec_addr: {'code': code}}] if code else [])
    return at(rpc('eth_call', params), 0)


def winner_block(user, send_block, our_hash):
    lo = max(0, send_block - 50)
    hi = max(send_block, int(rpc('eth_blockNumber', []), 16))
    logs = rpc('eth_getLogs', [{'address': SPOKE, 'fromBlock': hex(lo), 'toBlock': hex(hi),
                               'topics': [T_LIQ, None, None, '0x' + aw(user)]}])
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
    for _ in range(20):  # OP blocks are 2 s; give up after 20 s
        time.sleep(1)
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


def attempt(s, user, hf, why):
    now = time.time()
    if s['cooldown'].get(user, 0) > now:
        return
    s['cooldown'][user] = now + 600
    from_addr = owner() if MODE == 'live' else PAPER_OWNER
    exec_addr = EXEC if MODE == 'live' else PAPER_EXEC
    code = None if MODE == 'live' else RUNTIME
    debt, colls = position(user)
    if debt == 0 or not colls:
        log('candidate_skip', user=user, hf=hf / 1e18, reason='no_usdc_debt_or_no_collateral_in_scope')
        s['cooldown'][user] = now + 21600
        return
    # flash a little more than the debt: the spoke restores only what the target health factor
    # allows and the unused part goes straight back to Morpho
    cover = min(debt + debt // 100 + 10**6, MAX_COVER_USDC)
    best = None
    healthy = False
    for _, reserve in colls[:2]:
        for path in RESERVES[reserve][2]:
            try:
                gain = sim(calldata(reserve, user, cover, path, 1), from_addr, exec_addr, code)
            except ReadBudgetExceeded:
                raise
            except Exception as e:
                log('simulate_revert', user=user, why=why, hf=hf / 1e18, reserve=reserve, path=path,
                    error=str(e)[:200])
                if ERR_HEALTHY in str(e):
                    healthy = True
                    break
                continue
            if best is None or gain > best[0]:
                best = (gain, reserve, path)
        if healthy:
            break
    if best is None:
        # healthy again: look on the next poll; unsellable / too thin: do not burn reads on it
        s['cooldown'][user] = now + (10 if healthy else 3600)
        return
    gain, reserve, path = best
    gross_usd = gain / 1e6
    base_fee = int(rpc('eth_gasPrice', []), 16)
    priority = int(gross_usd * BID_SHARE / ETH_REF_USD * 1e18 / GAS_LIMIT)
    max_fee = min(MAX_FEE_WEI, base_fee * 2 + priority)
    priority = min(priority, max_fee)
    gas_cap_usd = GAS_LIMIT * max_fee / 1e18 * ETH_REF_USD + L1_FEE_USD
    if max_fee < base_fee or gas_cap_usd >= 1.0 or gross_usd <= gas_cap_usd:
        log('opportunity_skip', user=user, why=why, hf=hf / 1e18, gross_usd=gross_usd,
            gas_cap_usd=gas_cap_usd, base_fee=base_fee, reason='gross_not_above_gas_cap')
        s['cooldown'][user] = now + 3600
        return
    min_profit = int(gas_cap_usd * 1e6)
    data = calldata(reserve, user, cover, path, min_profit)
    try:
        gain = sim(data, from_addr, exec_addr, code)  # the exact bytes to send
    except ReadBudgetExceeded:
        raise
    except Exception as e:
        log('simulate_revert', user=user, why=why, hf=hf / 1e18, reserve=reserve, path=path, error=str(e)[:200])
        return
    log('opportunity', user=user, why=why, hf=hf / 1e18, reserve=reserve, collateral=RESERVES[reserve][0],
        path=path, cover_usdc=cover / 1e6, debt_usdc=debt / 1e6, gross_usd=gross_usd, gas_cap_usd=gas_cap_usd,
        max_fee=max_fee, priority=priority, simulated_gain=gain, mode=MODE, executor=exec_addr)
    if MODE == 'live':
        send_live(user, data, max_fee, priority, gross_usd)
    else:
        log('paper_sim', user=user, result='success', gain=gain)


def discover(s):
    """New borrowers since the last scan: Borrow logs on the spoke (one getLogs per 40,000 blocks)."""
    head = int(rpc('eth_blockNumber', []), 16)
    frm = s['scanned_to'] + 1
    known = set(s['users'])
    added = 0
    while frm <= head:
        to = min(frm + LOG_PAGE - 1, head)
        logs = rpc('eth_getLogs', [{'address': SPOKE, 'fromBlock': hex(frm), 'toBlock': hex(to),
                                   'topics': [T_BORROW]}])
        for x in logs:
            u = '0x' + x['topics'][3][26:].lower()
            if u not in known:
                known.add(u)
                s['users'].append(u)
                added += 1
        s['scanned_to'] = to
        frm = to + 1
    return added


def scan(s, users, label):
    try:
        rows = read_health(users)
    except ReadBudgetExceeded:
        raise
    except Exception as e:
        log('scan_error', label=label, error=str(e)[:200])
        return
    rows = [z for z in rows if z[2] >= MIN_DEBT_VALUE]
    if label == 'full':
        near = sorted(rows, key=lambda z: z[1])[:NEAR_MAX]
        s['near'] = [u for u, _, _ in near]
    # the lowest health factor still above the threshold decides the poll speed
    above = [z[1] for z in rows if z[1] >= 10**18]
    s['near_min_hf'] = min(above, default=0)
    cands = sorted([z for z in rows if z[1] < 10**18], key=lambda z: -z[2])
    log('scan', label=label, checked=len(users), debtors=len(rows), candidates=len(cands),
        near=len(s['near']), min_hf=min((z[1] for z in rows), default=0) / 1e18,
        min_hf_above_1=s['near_min_hf'] / 1e18)
    for u, hf, _ in cands[:5]:
        attempt(s, u, hf, label)


def feed_wait(cursor):
    """Long-poll the farm feed for AnswerUpdated on the three Chainlink aggregators (one filter:
    the same address list and topic on every call)."""
    q = {'address': ','.join(AGGS), 'topic0': T_ANSWER, 'timeout': '55'}
    if cursor:
        q['after'] = cursor
    with urllib.request.urlopen(f'{FEED}/logs/{CHAIN}?' + urllib.parse.urlencode(q), timeout=65) as r:
        return json.load(r)


def main():
    """Event-driven: a borrower's health factor crosses below 1 when the oracle price moves, and the
    price moves only when a Chainlink aggregator emits AnswerUpdated. The bot waits on the feed for
    that log and then re-reads the near set once. No timer decides when to look, except the 5-minute
    safety poll the feed rules require and the 12 h full scan that rebuilds the near set."""
    s = load_state()
    log('start', mode=MODE, users=len(s['users']), near=len(s['near']),
        executor=(EXEC if MODE == 'live' else PAPER_EXEC), trigger='feed AnswerUpdated', aggregators=AGGS)
    while True:
        now = time.time()
        try:
            if not s['last_full'] or now - s['last_full'] >= FULL_SCAN_INTERVAL:
                added = discover(s)
                log('discover', added=added, users=len(s['users']), scanned_to=s['scanned_to'])
                scan(s, s['users'], 'full')
                s['last_full'] = s['last_poll'] = now
            elif now - s['last_poll'] >= SAFETY_POLL:
                scan(s, s['near'], 'safety_poll')
                s['last_poll'] = now
            s['cooldown'] = {u: t for u, t in s['cooldown'].items() if t > now}
            save_state(s)
            result = feed_wait(s.get('feed_cursor'))
            s['feed_cursor'] = result.get('cursor', s.get('feed_cursor'))
            logs = result.get('logs') or []
            if result.get('gap') or any(x.get('removed') for x in logs):
                # the stream was interrupted or reorged: an update may have been missed, re-read state
                log('feed_gap', gap=bool(result.get('gap')), removed=sum(1 for x in logs if x.get('removed')))
                scan(s, s['near'], 'gap')
                s['last_poll'] = time.time()
            elif logs:
                ts = [int(x['blockTimestamp'], 16) for x in logs if x.get('blockTimestamp')]
                log('feed', events=len(logs), blocks=sorted({int(x['blockNumber'], 16) for x in logs}),
                    aggregators=sorted({x['address'].lower() for x in logs}),
                    delay_s=(round(time.time() - max(ts), 2) if ts else None))
                scan(s, s['near'], 'oracle_update')
                s['last_poll'] = time.time()
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, ConnectionError) as e:
            # feed 429 (filter slots full, CU cap) / 503 / connection error, or a relay error:
            # "you may have missed something" -> read the state once through the relay, then go on.
            # While the feed stays down this is a relay poll every FEED_DOWN_POLL seconds.
            log('feed_error', error=str(e)[:180])
            try:
                if time.time() - s.get('last_gap_scan', 0) >= FEED_DOWN_POLL:
                    s['last_gap_scan'] = time.time()
                    scan(s, s['near'], 'gap')
                    s['last_poll'] = time.time()
            except ReadBudgetExceeded as e2:
                log('read_budget', error=str(e2))
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
