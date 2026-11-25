#!/usr/bin/env python3
"""Trial: Aave V4 (Base spoke) liquidations through the TrialAave4Take executor.

Collateral is Coinbase tokenized equities, debt is USDC. The bot waits on the farm feed
for the equity price aggregators' AnswerUpdated events, reads the health factor of the
borrowers nearest the threshold with one Multicall3 read, simulates the executor call
(Morpho flash loan -> liquidationCall -> sell collateral on a UniV3 pool -> repay) and,
live, sends it. A lost attempt costs gas only (executor NoProfit guard).
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
SPOKE = '0x17905db0e4a3514467539956c084180616ae7b8d'
ORACLE = '0xabaf048fd7675ea34a84332371ffd5d55e322a47'   # spoke.ORACLE()
USDC = '0x833589fcd6edb6e08f4c7c32d4f71b54bda02913'
DEBT_RESERVE = 7                                          # USDC, the only borrowed reserve
MULTICALL = '0xca11bde05977b3631167028862be2a173976ca11'
# collateral reserves: id -> (symbol, underlying, [UniV3 pools vs USDC, deepest first])
RESERVES = {
    0: ('AAPLc', '0xb200000000000000000000c2e324d24d7eecd1fb', ['0x97f35d1e92795327614be000cd18cba1be2c1931']),
    1: ('AMZNc', '0xb200000000000000000000d9192b6b456483c2e8', ['0x7f030e5fd657795c0937a3e8af2929fd90da91c7']),
    2: ('GOOGLc', '0xb2000000000000000000002d0ba3164cc74f58b7', ['0x1f52f46bac657564c31122b12b43a459e09273c8',
                                                                '0x8634ee4145a63e40e44e12a6bb1b905fcb8856a6']),
    3: ('METAc', '0xb2000000000000000000008bc8786b856e61707c', ['0x583919ec1975a1238c50e1940911894ee6912476']),
    4: ('MSFTc', '0xb200000000000000000000ab99cfa739e253872b', ['0xd73cbecc0f62c7c1704332ed119514d6d84dc607']),
    5: ('NVDAc', '0xb20000000000000000000078ee7ce2fe4908108c', ['0x60661b315553eb81872deea9a66d567cf0ccd33b',
                                                               '0x9778aad868418ff6c996294ce62c9ed2b96896d1']),
    6: ('TSLAc', '0xb2000000000000000000001e800a7f5189430cd0', ['0xad6a86333c579d5bbd150f28e74651006fa87b3b']),
    8: ('SPCXc', '0xb2000000000000000000007b9fcbd005511acbd5', ['0x127a12fc0953ab2ab89558c67ba6d597d7140431']),
}
# aggregator() of each reserve's price source ("Coinbase AAPL" ... "Coinbase SPCX")
AGGS = ['0xc37b6f754e90d4cca1f533f5a08f7d532b3d0d9d', '0x4816cb7ee43ee12c0bc9d3c597246f34d5cfdb7c',
        '0x6bf33b7855eb8047dde206d9f6321d7d02cfb308', '0xa7155928bee40052efb3094a046c5498202fd3ee',
        '0xd72b34be6c2180ad0d28dbb415aefde8a55f3ed3', '0xf72b1eb5932800f3d2a5eec5f99e6cd586479675',
        '0x0288234d9311c33be6c3a34b051bff8a799daa82', '0xa994b7fc3123ae0ef4ee53ab5e3545f2639187a7']
T_ANSWER = '0x0559884fd3a460db3073b7fc896cc77986f16e378210ded43186175bf646fc5f'  # AnswerUpdated
T_LIQ = '0x2a1f12d996f530f89d8038aa293f9fde81cac44b6dfd6225e3358d09b78a4a37'     # spoke LiquidationCall
T_BORROW = '0xef18174796a5d2f91d51dc5e907a4d7867bbd6e800f6225168e0453d581d0dcd'  # spoke Borrow
SEL_TAKE = '0x3c749d76'
SEL_ACCOUNT = '0xbf92857c'     # getUserAccountData(address)
SEL_SUPPLIED = '0xf1568a89'    # getUserSuppliedAssets(uint256,address)
SEL_DEBT = '0x9b7172a6'        # getUserTotalDebt(uint256,address)
SEL_PRICE = '0xd45c35ff'       # oracle getReservePrice(uint256)
SEL_TRYAGG = '0xbce38bd7'
ERR_HEALTHY = '930bb771'       # HealthFactorNotBelowThreshold()
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
SEED = json.loads((HERE / 'seed-borrowers.json').read_text())   # {"head": block, "users": [..]}
BLOCK_TAG = 'latest'           # changed only by the offline self-test

# ---- loss guard (trial rule: every send's gas cap < 1 USD) ----
GAS_LIMIT = 800_000            # fork: success 530,156, NoProfit revert 629,354
MAX_FEE_WEI = 250_000_000      # 0.25 gwei hard cap: 800k x 0.25 gwei = 2.0e-4 ETH
ETH_REF_USD = 4000.0           # deliberately high ETH price: cap = 0.80 USD at 4000 (0.36 at 1,820)
L1_FEE_USD = 0.02              # allowance for the OP-stack L1 data fee of a ~300-byte tx
BID_SHARE = 0.25               # priority fee bid is at most 25% of simulated gross
MAX_COVER_USDC = 50_000 * 10**6    # flash size cap per take; larger debts are taken in part
NEAR_HF = 1.15 * 10**18        # borrowers below this health factor are re-read on every update
NEAR_MAX = 100
BATCH = 100
FULL_SCAN_INTERVAL = 21600     # every borrower + new Borrow logs every 6 h
SAFETY_POLL = 300
CU_COST = {'eth_call': 26, 'eth_getLogs': 75, 'eth_getTransactionReceipt': 20,
           'eth_blockNumber': 10, 'eth_gasPrice': 10}
CU_CAP = 80_000                # relay reads/day; the feed filter (~20k CU/day) is on top
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
    """One eth_call per BATCH users: getUserAccountData. Returns [(user, healthFactor, debtValueRay)]
    for users with debt (word 2 = healthFactor, word 4 = totalDebtValueRay, word 6 = borrowCount)."""
    rows = []
    for off in range(0, len(users), BATCH):
        batch = users[off:off + BATCH]
        res = try_aggregate([(SPOKE, SEL_ACCOUNT + aw(u)) for u in batch])
        for u, (ok, data) in zip(batch, res):
            if ok and len(data) >= 2 + 7 * 64 and at(data, 6) > 0:
                rows.append((u, at(data, 2), at(data, 4)))
    return rows


def position(user):
    """One eth_call: the user's USDC debt and, per collateral reserve, supplied assets x oracle price.
    Returns (debt in USDC units, [(value, reserveId)] largest first)."""
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
            vals.append((at(s_data, 0) * at(p_data, 0), i))
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
            'near': [], 'feed_cursor': None, 'last_full': 0, 'last_poll': 0, 'cooldown': {}}


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


def calldata(reserve, user, cover, pool, min_profit):
    token = RESERVES[reserve][1]
    return (SEL_TAKE + aw(SPOKE) + word(reserve) + word(DEBT_RESERVE) + aw(token) + aw(user)
            + word(cover) + aw(pool) + word(min_profit))


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
        log('candidate_skip', user=user, hf=hf / 1e18, reason='no_usdc_debt_or_collateral')
        s['cooldown'][user] = now + 21600
        return
    # flash a little more than the debt: the spoke restores only what the target health factor
    # allows and the unused part goes straight back to Morpho
    cover = min(debt + debt // 100 + 10**6, MAX_COVER_USDC)
    best = None
    healthy = False
    for _, reserve in colls[:2]:
        for pool in RESERVES[reserve][2]:
            try:
                gain = sim(calldata(reserve, user, cover, pool, 1), from_addr, exec_addr, code)
            except ReadBudgetExceeded:
                raise
            except Exception as e:
                log('simulate_revert', user=user, why=why, hf=hf / 1e18, reserve=reserve, pool=pool,
                    error=str(e)[:200])
                if ERR_HEALTHY in str(e):
                    healthy = True
                    break
                continue
            if best is None or gain > best[0]:
                best = (gain, reserve, pool)
        if healthy:
            break
    if best is None:
        # healthy again: look on the next update; unsellable / too thin: do not burn reads on it
        s['cooldown'][user] = now + (20 if healthy else 3600)
        return
    gain, reserve, pool = best
    gross_usd = gain / 1e6
    base_fee = int(rpc('eth_gasPrice', []), 16)
    priority = int(gross_usd * BID_SHARE / ETH_REF_USD * 1e18 / GAS_LIMIT)
    max_fee = min(MAX_FEE_WEI, base_fee * 2 + priority)
    priority = min(priority, max_fee)
    gas_cap_usd = GAS_LIMIT * max_fee / 1e18 * ETH_REF_USD + L1_FEE_USD
    if max_fee < base_fee or gas_cap_usd >= 1.0 or gross_usd <= gas_cap_usd:
        log('opportunity_skip', user=user, why=why, hf=hf / 1e18, gross_usd=gross_usd,
            gas_cap_usd=gas_cap_usd, base_fee=base_fee, reason='gross_not_above_gas_cap')
        return
    min_profit = int(gas_cap_usd * 1e6)
    data = calldata(reserve, user, cover, pool, min_profit)
    try:
        gain = sim(data, from_addr, exec_addr, code)  # the exact bytes to send
    except ReadBudgetExceeded:
        raise
    except Exception as e:
        log('simulate_revert', user=user, why=why, hf=hf / 1e18, reserve=reserve, pool=pool, error=str(e)[:200])
        return
    log('opportunity', user=user, why=why, hf=hf / 1e18, reserve=reserve, collateral=RESERVES[reserve][0],
        pool=pool, cover_usdc=cover / 1e6, debt_usdc=debt / 1e6, gross_usd=gross_usd, gas_cap_usd=gas_cap_usd,
        max_fee=max_fee, priority=priority, simulated_gain=gain, mode=MODE)
    if MODE == 'live':
        send_live(user, data, max_fee, priority, gross_usd)
    else:
        log('paper_sim', user=user, result='success', gain=gain)


def discover(s):
    """New borrowers since the last scan: Borrow logs on the spoke (one or a few getLogs per full scan)."""
    head = int(rpc('eth_blockNumber', []), 16)
    frm = s['scanned_to'] + 1
    known = set(s['users'])
    added = 0
    while frm <= head:
        to = min(frm + 499_999, head)
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
    if label == 'full':
        near = sorted([z for z in rows if z[1] < NEAR_HF], key=lambda z: z[1])[:NEAR_MAX]
        s['near'] = [u for u, _, _ in near]
    cands = sorted([z for z in rows if z[1] < 10**18], key=lambda z: -z[2])
    log('scan', label=label, checked=len(users), debtors=len(rows), candidates=len(cands),
        near=len(s['near']), min_hf=min((z[1] for z in rows), default=0) / 1e18)
    for u, hf, _ in cands[:5]:
        attempt(s, u, hf, label)


def feed_wait(cursor):
    q = {'address': ','.join(AGGS), 'topic0': T_ANSWER, 'timeout': '55'}
    if cursor:
        q['after'] = cursor
    with urllib.request.urlopen(f'{FEED}/logs/{CHAIN}?' + urllib.parse.urlencode(q), timeout=65) as r:
        return json.load(r)


def main():
    s = load_state()
    log('start', mode=MODE, users=len(s['users']), near=len(s['near']))
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
            if result.get('gap') or any(x.get('removed') for x in result.get('logs', [])):
                scan(s, s['near'], 'gap')
                s['last_poll'] = time.time()
            elif result.get('logs'):
                log('feed', events=len(result['logs']),
                    blocks=sorted({int(x['blockNumber'], 16) for x in result['logs']}),
                    aggregators=sorted({x['address'][:10] for x in result['logs']}))
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
