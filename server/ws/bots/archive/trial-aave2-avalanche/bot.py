#!/usr/bin/env python3
"""trial-aave2-avalanche: cheap-chain trial of Aave v2 Avalanche liquidations (USDC.e, USDT.e or DAI.e debt).

Aave v2 Avalanche is a frozen market that still liquidates about 2.7 positions a day. The bot waits on the farm
feed for LendingPool LiquidationCall logs plus a 60 s safety scan of the near-HF list. For an underwater user it
simulates the exact executor call (flash loan from the v2 pool itself -> liquidationCall -> Trader Joe V1 pair
sale of the seized collateral -> the pool pulls loan + premium -> pair sale of the surplus for native USDC) and,
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
CHAIN = 'avalanche'
FEED = 'http://127.0.0.1:8546/logs/avalanche'

POOL = '0x4f01aed16d97e3ab5ab2b501154dc9bb0f1a5a2c'       # Aave v2 LendingPool (Avalanche), aave-address-book AaveV2Avalanche
MULTICALL = '0xca11bde05977b3631167028862be2a173976ca11'
WAVAX = '0xb31f66aa3c1e785363f0875a1b74e27b85fd66c7'      # wrapped native, prices the gas
WETH = '0x49d5c2bdffac6ce2bfdb6640f4f80f226bc10bab'       # WETH.e
WBTC = '0x50b7545627a5162f82a992c33b87adc75187b218'       # WBTC.e
USDCE = '0xa7d7079b0fead91f3e65f86e8915cb59c1a4c664'      # bridged USDC.e, the v2 market's USDC
USDTE = '0xc7198437980c041c805a1edcba50c1ce5db95118'      # USDT.e
DAIE = '0xd586e7f844cea2f87f50152665bcbc2c279d8d70'       # DAI.e
USDC = '0xb97ef9ef8734c71904d8002f8b6bc66dd9c48a6e'       # native USDC, the farm's avalanche USDC: profit is paid in it
DEBTS = {USDCE: 6, USDTE: 6, DAIE: 18}                    # debt token -> decimals (all priced at 1 USD for sizing)
STABLES = (USDCE, USDTE, DAIE)
COLLATERALS = (WETH, WBTC, WAVAX, USDCE, DAIE, USDTE)
# Trader Joe V1 pairs (factory 0x9ad6c38be94206ca50bb0d90783181662f0cfa10 getPair, read 2026-11-19; 0.3 % fee)
PAIR = {
    frozenset((USDCE, USDC)): '0x2a8a315e82f85d1f0658c5d66a452bbdd9356783',
    frozenset((USDCE, USDTE)): '0x2e02539203256c83c7a9f6fa6f8608a32a2b1ca2',
    frozenset((USDCE, DAIE)): '0x63abe32d0ee76c05a11838722a63e012008416e6',
    frozenset((USDTE, DAIE)): '0xa6908c7e3be8f4cd2eb704b5cb73583ebf56ee62',
    frozenset((USDCE, WAVAX)): '0xa389f9430876455c36478deea9769b7ca4e3ddb1',
    frozenset((USDTE, WAVAX)): '0xed8cbd9f0ce3c6986b22002f03c6475ceb7a6256',
    frozenset((DAIE, WAVAX)): '0x87dee1cc9ffd464b79e058ba20387c1984aed86a',
    frozenset((USDC, WAVAX)): '0xf4003f4efbe8691b60249e6afbd307abe7758adb',
    frozenset((WETH, WAVAX)): '0xfe15c2695f1f920da45c30aae47d11de51007af9',
    frozenset((WBTC, WAVAX)): '0xd5a37dc5c9a396a03dd1136fc76a1a02b1c88ffa',
    frozenset((WETH, USDCE)): '0x199fb78019a08af2cb6a078409d0c8233eba8a0c',
}
FEE_NUM = 997
# Share of the user's total debt offered as cover, largest first. Aave caps the repayment at what it allows, but the
# flash premium (9 bps) is paid on the whole loan, so both the over-cover and the half are simulated and the better
# one is kept. Large debts also get smaller sizes because the seized collateral is sold in thin V2 pairs: the sweep
# stops at the first size that gains less than the one before.
COVER_SHARES = (1.03, 0.52, 0.25, 0.12, 0.06, 0.03)
SWEEP_MIN_USD = 2000                 # debts under this get only the first two sizes
LIQ_TOPIC = '0xe413a321e8681d831f4dbccbca790d2952b56f977908e45be37335533e005286'
# liquidate((address,address,address,address,address[],address,address[],uint256),uint256,uint256), cast sig
SEL_LIQUIDATE = '0xfab413e0'

PAPER_EXEC = '0xb464f7314d55ec6a9a0cf6f7f6df17af8ed5b352'   # fork deployment; paper code override only
PAPER_OWNER = '0xc0ffee0000000000000000000000000000000001'
EXEC = os.environ.get('EXECUTOR_ADDR_AVALANCHE') or os.environ.get('EXECUTOR_ADDR')
if MODE == 'live' and not EXEC:
    raise SystemExit('EXECUTOR_ADDR_AVALANCHE or EXECUTOR_ADDR is required in live mode')
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
MAX_FEE_WEI = 500 * 10**9  # 500 gwei absolute ceiling for maxFeePerGas (the USD cap binds first)
MIN_TIP_WEI = 10**9        # a bid under 1 gwei is not worth a send
BID_SHARE = 0.50           # priority fee bid: at most this share of the simulated gross
# flash-loaned from the v2 pool, never the bot's own funds (aTokens held 588k USDC.e, 313k USDT.e, 215k DAI.e on 11-19)
MAX_COVER = {USDCE: 200_000 * 10**6, USDTE: 100_000 * 10**6, DAIE: 70_000 * 10**18}
MIN_DEBT_BASE = 2 * 10**8  # skip users with less than 2 USD of debt (Aave v2 Avalanche base currency: USD, 8 decimals)
RELAY_CU_CAP = 75_000      # per UTC day; the feed's own CU is metered separately

# Retry delays per user. Positions that stay under water with nothing to gain (bad debt, dust, unsupported
# assets) must not eat the read budget: about 28 such users existed on 2026-11-19.
COOL_DEFAULT = 600
COOL_DUST = 2 * 3600
COOL_NO_ROUTE = 6 * 3600
COOL_UNSUPPORTED = 24 * 3600
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
    """One Multicall3 tryAggregate(false, calls) of LendingPool.getUserAccountData(user). Returns [(debtBase, hf)]."""
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
    idx = {addr_of(h[2 + (2 + i) * 64:2 + (3 + i) * 64]): i for i in range(n)}
    if USDCE not in idx or WAVAX not in idx:
        raise RuntimeError('Aave v2 reserve list lacks USDC.e/WAVAX')
    return idx


def prices():
    """(USD per AVAX, USD per unit of the oracle's base currency) from the Aave v2 oracle; unit-free: both are
    ratios to the oracle's USDC.e price."""
    provider = addr_of(call(POOL, '0xfe65acfe'))       # getAddressesProvider()
    oracle = addr_of(call(provider, '0xfca513a8'))     # getPriceOracle()
    usdc_p = at(call(oracle, '0xb3596f07' + aword(USDCE)), 0)   # getAssetPrice(USDC.e), base units per whole token
    avax_p = at(call(oracle, '0xb3596f07' + aword(WAVAX)), 0)
    if usdc_p <= 0 or avax_p <= 0:
        return 0.0, 0.0
    return avax_p / usdc_p, 1 / usdc_p


def pair(a, b):
    return PAIR[frozenset((a, b))]


def routes_in(coll, debt):
    """Candidate collateral -> debt pair chains, at most three per pair of assets."""
    if coll == debt:
        return [[]]
    via = [pair(coll, WAVAX), pair(WAVAX, debt)] if WAVAX not in (coll, debt) else None
    out = []
    if frozenset((coll, debt)) in PAIR:
        out.append([pair(coll, debt)])
    if via:
        out.append(via)
    return out


def routes_out(debt):
    """Candidate debt -> native USDC pair chains."""
    if debt == USDCE:
        return [[pair(USDCE, USDC)]]
    return [[pair(debt, USDCE), pair(USDCE, USDC)], [pair(debt, WAVAX), pair(WAVAX, USDC)]]


def calldata(user, coll, debt, pairs_in, pairs_out, cover, min_profit):
    """ABI encoding of liquidate(Job, cover, minProfit); Job is a dynamic tuple (checked against cast in selftest)."""
    arr_in = word(len(pairs_in)) + ''.join(aword(p) for p in pairs_in)
    arr_out = word(len(pairs_out)) + ''.join(aword(p) for p in pairs_out)
    job = (aword(POOL) + aword(user) + aword(coll) + aword(debt) + word(8 * 32) + aword(USDC)
           + word(8 * 32 + len(arr_in) // 2) + word(FEE_NUM) + arr_in + arr_out)
    return SEL_LIQUIDATE + word(3 * 32) + word(cover) + word(min_profit) + job


def exec_ctx():
    if MODE == 'live':
        return bot_address(), EXEC, None
    return PAPER_OWNER, PAPER_EXEC, {PAPER_EXEC: {'code': RUNTIME}}


def sim(data, ctx):
    frm, to, ov = ctx
    params = [{'from': frm, 'to': to, 'data': data, 'gas': hex(3_000_000)}, 'latest'] + ([ov] if ov else [])
    return at(rpc('eth_call', params), 0)


def estimate(data, ctx):
    frm, to, ov = ctx
    params = [{'from': frm, 'to': to, 'data': data}, 'latest'] + ([ov] if ov else [])
    return int(rpc('eth_estimateGas', params), 16)


def healthy_revert(msg):
    # Aave v2 LendingPoolCollateralManager error 42 = health factor not below the threshold
    return 'reverted: 42' in msg or '00023432' in msg


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
    s['cooldown'][user] = now + COOL_DEFAULT
    cfg = at(call(POOL, '0x4417a583' + aword(user)), 0)  # getUserConfiguration(user)
    debts = [t for t in DEBTS if t in idx and cfg >> (2 * idx[t]) & 1]
    colls = [t for t in COLLATERALS if t in idx and cfg >> (2 * idx[t] + 1) & 1]
    if not debts or not colls:
        s['cooldown'][user] = now + COOL_UNSUPPORTED
        log('opportunity_skip', user=user, hf=hf, reason='unsupported_assets', trigger=trigger)
        return
    avax_usd, base_usd = prices()
    if avax_usd <= 0:
        return
    debt_usd = debt_base * base_usd
    ctx = exec_ctx()
    best = None
    for debt in debts:
        p_out_fixed = None   # debt -> native USDC route, fixed by the first simulation that works
        shares = COVER_SHARES if debt_usd >= SWEEP_MIN_USD else COVER_SHARES[:2]
        for coll in colls:
            for p_in in routes_in(coll, debt):
                prev, last_cover = None, None
                for share in shares:
                    usd = debt_usd * share + (1 if share > 1 else 0)
                    cover = min(int(usd * 10 ** DEBTS[debt]), MAX_COVER[debt])
                    if cover <= 0 or cover == last_cover:
                        continue
                    last_cover = cover
                    gain, p_out = None, None
                    for cand in ([p_out_fixed] if p_out_fixed else routes_out(debt)):
                        p_out = cand
                        try:
                            gain = sim(calldata(user, coll, debt, p_in, p_out, cover, 0), ctx)
                            p_out_fixed = cand
                            break
                        except ReadBudgetExceeded:
                            raise
                        except Exception as e:
                            log('simulate_revert', user=user, debt=debt, collateral=coll, pairs_in=p_in, pairs_out=cand,
                                hf=hf, cover=cover, error=str(e)[:160])
                            if healthy_revert(str(e)):
                                return   # the user is healthy again (or was taken): no route or size can work
                    if gain is None:
                        break        # this route does not work at this size; next route
                    g = gain / 1e6   # native USDC, 6 decimals
                    if best is None or g > best[0]:
                        best = (g, debt, coll, p_in, p_out, cover, gain)
                    if prev is not None and g <= prev:
                        break        # past the peak: the gain now falls with the cover
                    prev = g
    if best is None:
        s['cooldown'][user] = now + COOL_NO_ROUTE
        log('opportunity_skip', user=user, hf=hf, debt_usd=debt_usd, reason='no_profitable_route', trigger=trigger)
        return
    gross_usd, debt, coll, p_in, p_out, cover, gain = best
    try:
        gas_limit = estimate(calldata(user, coll, debt, p_in, p_out, cover, 0), ctx) * 5 // 4
        base_price = int(rpc('eth_gasPrice', []), 16)
    except ReadBudgetExceeded:
        raise
    except Exception as e:
        log('simulate_revert', user=user, debt=debt, collateral=coll, hf=hf, error='estimate: ' + str(e)[:140])
        return
    # Fee ceiling so that maxFeePerGas x gasLimit < MAX_TX_USD (and never above MAX_FEE_WEI).
    # 2 x eth_gasPrice leaves room for base-fee growth between the read and inclusion.
    fee_ceiling = min(MAX_FEE_WEI, int(MAX_TX_USD * 0.98 / avax_usd * 1e18 / gas_limit))
    priority = int(gross_usd * BID_SHARE / avax_usd * 1e18 / gas_limit)       # bid <= BID_SHARE of gross
    priority = min(priority, fee_ceiling - 2 * base_price)
    if priority < MIN_TIP_WEI:
        s['cooldown'][user] = now + COOL_DUST
        log('opportunity_skip', user=user, debt=debt, collateral=coll, hf=hf, gross_usd=gross_usd,
            reason='bid_under_min_tip', trigger=trigger)
        return
    max_fee = min(fee_ceiling, 2 * base_price + priority)
    gas_cap_usd = gas_limit * max_fee / 1e18 * avax_usd
    if max_fee < base_price + priority or gas_cap_usd >= MAX_TX_USD or gross_usd <= gas_cap_usd:
        s['cooldown'][user] = now + COOL_DUST
        log('opportunity_skip', user=user, debt=debt, collateral=coll, hf=hf, gross_usd=gross_usd,
            gas_cap_usd=gas_cap_usd, reason='gross_not_above_gas_cap', trigger=trigger)
        return
    # On-chain floor: the executor reverts unless the gain covers the signed gas cap.
    min_profit = int(gas_cap_usd * 1e6) + 1
    data = calldata(user, coll, debt, p_in, p_out, cover, min_profit)
    try:
        gain = sim(data, ctx)  # the exact bytes that would be sent
    except ReadBudgetExceeded:
        raise
    except Exception as e:
        log('simulate_revert', user=user, debt=debt, collateral=coll, hf=hf, error='final: ' + str(e)[:140])
        return
    log('opportunity', user=user, debt=debt, collateral=coll, pairs_in=p_in, pairs_out=p_out, hf=hf, cover=cover,
        debt_usd=debt_usd, gross_usd=gross_usd, gas_cap_usd=gas_cap_usd, gas_limit=gas_limit, max_fee=max_fee,
        priority=priority, min_profit=min_profit, simulated_gain=gain, trigger=trigger, mode=MODE)
    if MODE == 'live':
        send_live(user, coll, debt, data, gas_limit, max_fee, priority, gross_usd, gas_cap_usd)
    else:
        log('paper_sim', user=user, debt=debt, collateral=coll, result='success', gain=gain, gross_usd=gross_usd)


def scan_users(s, users, idx, label):
    eligible, near, debtors = [], [], []
    for off in range(0, len(users), 200):
        batch = users[off:off + 200]
        try:
            data = aggregate(batch)
        except ReadBudgetExceeded:
            raise
        except Exception as e:
            log('scan_error', label=label, offset=off, error=str(e)[:200])
            debtors += batch      # keep unread users in the universe
            continue
        for a, (debt, hf) in zip(batch, data):
            if debt > 0:
                debtors.append(a)
            if debt >= MIN_DEBT_BASE and hf > 0:
                near.append((hf, a))
                if hf < 10**18:
                    eligible.append((debt, hf, a))
    if label == 'full':
        near.sort(key=lambda z: abs(z[0] - 10**18))
        s['near'] = [a for _, a in near[:NEAR_COUNT]]
        s['users'] = sorted(set(debtors))   # the market is frozen: an address without debt cannot borrow again
    log('scan', label=label, checked=len(users), debtors=len(near), underwater=len(eligible), near=len(s['near']),
        universe=len(s['users']))
    eligible.sort(reverse=True)  # largest debt first
    now = time.time()
    eligible = [e for e in eligible if s['cooldown'].get(e[2], 0) <= now]   # users in cooldown do not use up the 3 slots
    for debt, hf, a in eligible[:3]:
        attempt(s, a, hf / 1e18, debt, idx, label)


def discover(s):
    """New universe members from the pool's own logs: the user of every LiquidationCall, and topics[2] of the
    other user events (Deposit / Borrow: onBehalfOf, Withdraw / Repay: user). Addresses without debt are dropped
    again by the next full scan."""
    head = int(rpc('eth_blockNumber', []), 16)
    start = s['cursor_block'] + 1 if s['cursor_block'] is not None else head - 3000
    start = max(start, head - 3000)   # at most ~45 min of 0.9 s blocks per request
    if start > head:
        return
    logs = rpc('eth_getLogs', [{'address': POOL, 'fromBlock': hex(start), 'toBlock': hex(head)}])
    users = set(s['users'])
    fresh = set()
    for lg in logs:
        t = lg.get('topics', [])
        if not t:
            continue
        if t[0] == LIQ_TOPIC and len(t) > 3:
            a = addr_of(t[3])
        elif len(t) > 2:
            a = addr_of(t[2])
        else:
            continue
        if a not in users:
            fresh.add(a)
    s['users'] = sorted(users | fresh)
    s['near'] = list(dict.fromkeys(s['near'] + sorted(fresh)))[:NEAR_COUNT + 100]  # watched until the next full scan
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
    idx = None   # reserve list is read inside the loop: every relay read sits under the read-budget handler
    while True:
        now = time.time()
        try:
            if idx is None:
                idx = reserves()
                log('start', mode=MODE, executor=(EXEC if MODE == 'live' else PAPER_EXEC), universe=len(s['users']),
                    reserve_index={t: idx.get(t) for t in (USDCE, USDTE, DAIE, WETH, WBTC, WAVAX)})
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
        except ReadBudgetExceeded as e:
            log('read_budget', error=str(e))
            tomorrow = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=1)).replace(
                hour=0, minute=0, second=5, microsecond=0)
            time.sleep(max(60, (tomorrow - datetime.datetime.now(datetime.timezone.utc)).total_seconds()))
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
            log('feed_error', error=str(e)[:180])   # 429/503/timeout: fall back to a state re-read
            try:
                if idx is not None:
                    scan_users(s, s['near'], idx, 'gap')
            except ReadBudgetExceeded as e2:
                log('read_budget', error=str(e2))
                time.sleep(600)
            except Exception as e2:
                log('scan_error', label='gap', error=str(e2)[:180])
            time.sleep(5)
        except Exception as e:
            log('loop_error', error=str(e)[:250])
            time.sleep(5)
        save_state(s)


if __name__ == '__main__':
    main()
