#!/usr/bin/env python3
"""trial-aave-polygon: cheap-chain trial of Aave v3 Polygon liquidations (native-USDC debt).

Waits on the farm feed for Pool LiquidationCall logs (a price flip that liquidates one user usually
puts others under water) plus a 60 s safety scan of the near-HF list. For an underwater user it
simulates the exact executor call (Morpho flash loan -> liquidationCall -> UniV3 swap -> repay) and,
in live mode, sends it when simulated gross > the signed gas cap. A lost attempt costs gas only.
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
CHAIN = 'polygon'
FEED = 'http://127.0.0.1:8546/logs/polygon'

POOL = '0x794a61358d6845594f94dc1db02a252b5b4814ad'       # Aave v3 Pool (Polygon), aave-address-book AaveV3Polygon
MORPHO = '0x1bf0c2541f820e775182832f06c0b7fc27a25f67'     # Morpho Blue (Polygon), fee-free flash loans
ROUTER = '0x68b3465833fb72a70ecdf485e0e4c7bd8665fc45'     # Uniswap V3 SwapRouter02 (Polygon)
MULTICALL = '0xca11bde05977b3631167028862be2a173976ca11'
WPOL = '0x0d500b1d8e8ef31e21c99d1db9a6444d3adf1270'       # wrapped native, prices the gas
WETH = '0x7ceb23fd6bc0add59e62ac25578270cff1b9f619'
WBTC = '0x1bfd67037b42cf73acf2047067bd4f2c47d9bfd6'
USDC = '0x3c499c542cef5e3811e1192ce70d8cc03d5c3359'       # native USDC, the farm's polygon USDC
DEBTS = (USDC,)                      # profit is paid in the debt token, so only native-USDC debt is taken
COLLATERALS = (WBTC, WETH, WPOL, USDC)
# Share of the user's total debt offered as cover, largest first. The seized collateral is sold in one UniV3
# pool, so past some size the slippage is larger than the liquidation bonus and the flash-loan repayment
# fails (Morpho "transferFrom reverted"; measured on OP Mainnet at block 159471567: 31,029 USD debt, covers
# of 16k and 32k revert, 8k gains 155.6 USDC, 5.6k gains 199.2). Gain rises, then falls, as the cover
# shrinks: the sweep stops at the first size that gains less than the one before.
COVER_SHARES = (1.03, 0.5, 0.25, 0.12, 0.06, 0.03)
HF_NOT_BELOW = '930bb771'            # Aave HealthFactorNotBelowThreshold(), cast sig
SWEEP_MIN_USD = 2000                 # debts under this get only the full over-cover (one simulation per route)
FEES = (500, 3000)                  # UniV3 fee tiers tried for collateral -> debt
LIQ_TOPIC = '0xe413a321e8681d831f4dbccbca790d2952b56f977908e45be37335533e005286'
BORROW_TOPIC = '0xb3d084820fb1a9decffb176436bd02558d15fac9b0ddfed8c465bc7359d7dce0'
WITHDRAW_TOPIC = '0x3115d1449a7b732c986cba18244e897a450f61e1bb8d589cd2e69e6c8924f9f7'
SEL_LIQUIDATE = '0x69670f05'  # liquidate(address,(address,address,address,address,address,uint24),uint256,uint256,bool)

PAPER_EXEC = '0xb464f7314d55ec6a9a0cf6f7f6df17af8ed5b352'   # fork deployment; paper code override only
PAPER_OWNER = '0xc0ffee0000000000000000000000000000000001'
EXEC = os.environ.get('EXECUTOR_ADDR_POLYGON') or os.environ.get('EXECUTOR_ADDR')
if MODE == 'live' and not EXEC:
    raise SystemExit('EXECUTOR_ADDR_POLYGON or EXECUTOR_ADDR is required in live mode')
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
MAX_TX_USD = 0.90          # signed gas cap (maxFeePerGas x gasLimit) stays under this
MAX_FEE_WEI = 20_000 * 10**9  # 20,000 gwei absolute ceiling for maxFeePerGas (the USD cap binds first)
MIN_TIP_WEI = 30 * 10**9   # Polygon validators drop transactions tipping under about 25-30 gwei
BID_SHARE = 0.50           # priority fee bid: at most this share of the simulated gross
MAX_COVER = {USDC: 60_000_000_000}  # flash-loaned, never the bot's own funds (Morpho held 127k USDC on 11-17)
MIN_DEBT_BASE = 5 * 10**8  # skip users with less than 5 USD of debt (Aave base currency, 8 decimals)
RELAY_CU_CAP = 75_000      # per UTC day; the feed's own CU is metered separately

NEAR_COUNT = 200
SCAN_INTERVAL = 3600
POLL_INTERVAL = 50         # with the 55 s feed timeout the safety cadence is ~55-60 s
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


def native_price_usd():
    provider = addr_of(call(POOL, '0x0542975c'))       # ADDRESSES_PROVIDER()
    oracle = addr_of(call(provider, '0xfca513a8'))     # getPriceOracle()
    return at(call(oracle, '0xb3596f07' + aword(WPOL)), 0) / 1e8  # getAssetPrice(WPOL): USD per POL


def calldata(user, coll, debt, fee, cover, min_profit):
    unwrap = False   # the debt token is always USDC here; the gain is paid out as USDC
    return (SEL_LIQUIDATE + aword(MORPHO) + aword(POOL) + aword(user) + aword(coll) + aword(debt)
            + aword(ROUTER) + word(fee) + word(cover) + word(min_profit) + word(int(unwrap)))


def exec_ctx():
    if MODE == 'live':
        return bot_address(), EXEC, None
    return PAPER_OWNER, PAPER_EXEC, {PAPER_EXEC: {'code': RUNTIME}}


def sim(data, ctx):
    frm, to, ov = ctx
    params = [{'from': frm, 'to': to, 'data': data, 'gas': hex(2_000_000)}, 'latest'] + ([ov] if ov else [])
    return at(rpc('eth_call', params), 0)


def estimate(data, ctx):
    frm, to, ov = ctx
    params = [{'from': frm, 'to': to, 'data': data}, 'latest'] + ([ov] if ov else [])
    return int(rpc('eth_estimateGas', params), 16)


def gross_usd_of(debt, gain, pol_usd):
    return gain / 1e6   # debt is always native USDC (6 decimals)


def winner_block(user, send_block, our_hash):
    """Block of the LiquidationCall that took this user near our send (ours if we won)."""
    head = int(rpc('eth_blockNumber', []), 16)
    logs = rpc('eth_getLogs', [{'address': POOL, 'fromBlock': hex(max(0, send_block - 300)), 'toBlock': hex(head),
                                'topics': [LIQ_TOPIC, None, None, '0x' + aword(user)]}])
    ours = [int(x['blockNumber'], 16) for x in logs if x['transactionHash'].lower() == our_hash.lower()]
    if ours:
        return min(ours), None
    if not logs:
        return None, None
    first = min(logs, key=lambda x: int(x['blockNumber'], 16))
    return int(first['blockNumber'], 16), first['transactionHash']


def send_live(user, coll, debt, data, gas_limit, max_fee, priority, gross_usd, gas_cap_usd):
    import farmbot_signer
    reply = farmbot_signer.send(CHAIN, EXEC, data, 0, gas_limit, max_fee, max_priority_fee_per_gas=priority)
    h = None
    if isinstance(reply, dict):
        h = reply.get('txHash') or reply.get('tx_hash') or reply.get('hash')
    if not h:
        log('signer_reject', user=user, debt=debt, collateral=coll, reply=reply)  # final, never retried
        return
    log('send', hash=h, user=user, debt=debt, collateral=coll, gas_limit=gas_limit, max_fee=max_fee,
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
    eth_usd = native_price_usd()   # USD per POL; the name is kept from the Base version
    if eth_usd <= 0:
        return
    ctx = exec_ctx()
    best = None
    for debt in debts:
        # Over-cover the whole debt first: Aave caps the repayment (close factor), the rest of the flash loan
        # goes straight back. A cover just under a small debt reverts MustNotLeaveDust(), so small debts get
        # only that one size. Large debts also get smaller covers (see COVER_SHARES).
        shares = COVER_SHARES if debt_base / 1e8 >= SWEEP_MIN_USD else COVER_SHARES[:1]
        for coll in colls:
            for fee in ((0,) if coll == debt else FEES):
                prev, last_cover = None, None
                for share in shares:
                    usd = debt_base / 1e8 * share + (1 if share > 1 else 0)
                    cover = min(int(usd * 1e6), MAX_COVER[debt])
                    if cover <= 0 or cover == last_cover:
                        continue
                    last_cover = cover
                    data = calldata(user, coll, debt, fee, cover, 0)
                    try:
                        gain = sim(data, ctx)
                    except ReadBudgetExceeded:
                        raise
                    except Exception as e:
                        log('simulate_revert', user=user, debt=debt, collateral=coll, fee=fee, hf=hf, cover=cover,
                            error=str(e)[:160])
                        if HF_NOT_BELOW in str(e):
                            return   # the user is healthy again (or was taken): no route or size can work
                        continue
                    g = gross_usd_of(debt, gain, eth_usd)
                    if best is None or g > best[0]:
                        best = (g, debt, coll, fee, cover, gain)
                    if prev is not None and g <= prev:
                        break    # past the peak: the gain now falls with the cover
                    prev = g
    if best is None:
        return
    gross_usd, debt, coll, fee, cover, gain = best
    try:
        gas_limit = estimate(calldata(user, coll, debt, fee, cover, 0), ctx) * 5 // 4
        base_price = int(rpc('eth_gasPrice', []), 16)
    except ReadBudgetExceeded:
        raise
    except Exception as e:
        log('simulate_revert', user=user, debt=debt, collateral=coll, fee=fee, hf=hf, error='estimate: ' + str(e)[:140])
        return
    # Fee ceiling so that maxFeePerGas x gasLimit < MAX_TX_USD (and never above MAX_FEE_WEI).
    # eth_gasPrice on Polygon = base fee + a suggested tip, so 2 x base_price leaves room for base-fee growth.
    fee_ceiling = min(MAX_FEE_WEI, int(MAX_TX_USD * 0.98 / eth_usd * 1e18 / gas_limit))
    priority = int(gross_usd * BID_SHARE / eth_usd * 1e18 / gas_limit)       # bid <= BID_SHARE of gross
    priority = min(priority, fee_ceiling - 2 * base_price)
    if priority < MIN_TIP_WEI:
        log('opportunity_skip', user=user, debt=debt, collateral=coll, hf=hf, gross_usd=gross_usd,
            reason='bid_under_min_tip', trigger=trigger)   # half the gross does not pay Polygon's minimum tip
        return
    max_fee = min(fee_ceiling, 2 * base_price + priority)
    gas_cap_usd = gas_limit * max_fee / 1e18 * eth_usd
    if max_fee < base_price + priority or gas_cap_usd >= MAX_TX_USD or gross_usd <= gas_cap_usd:
        log('opportunity_skip', user=user, debt=debt, collateral=coll, hf=hf, gross_usd=gross_usd,
            gas_cap_usd=gas_cap_usd, reason='gross_not_above_gas_cap', trigger=trigger)
        return
    # On-chain floor: the executor reverts unless the gain covers the signed gas cap.
    min_profit = int(gas_cap_usd * 1e6) + 1
    data = calldata(user, coll, debt, fee, cover, min_profit)
    try:
        gain = sim(data, ctx)  # the exact bytes that would be sent
    except ReadBudgetExceeded:
        raise
    except Exception as e:
        log('simulate_revert', user=user, debt=debt, collateral=coll, fee=fee, hf=hf, error='final: ' + str(e)[:140])
        return
    log('opportunity', user=user, debt=debt, collateral=coll, fee=fee, hf=hf, cover=cover, gross_usd=gross_usd,
        gas_cap_usd=gas_cap_usd, gas_limit=gas_limit, max_fee=max_fee, priority=priority, min_profit=min_profit,
        simulated_gain=gain, trigger=trigger, mode=MODE)
    if MODE == 'live':
        send_live(user, coll, debt, data, gas_limit, max_fee, priority, gross_usd, gas_cap_usd)
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
    start = max(start, head - 3000)   # at most ~100 min of 2 s blocks per request
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
    if WPOL not in idx or USDC not in idx:
        raise SystemExit('Aave reserve list lacks WPOL/USDC')
    log('start', mode=MODE, executor=(EXEC if MODE == 'live' else PAPER_EXEC), universe=len(s['users']),
        reserve_index={t: idx.get(t) for t in (USDC, WBTC, WETH, WPOL)})
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
            log('feed_error', error=str(e)[:180])   # 429/503/timeout: fall back to a state re-read
            try:
                scan_users(s, s['near'], idx, 'gap')
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
