#!/usr/bin/env python3
"""trial-benqi-avalanche: cheap-chain trial of Benqi Lending (Compound v2 fork) liquidations on Avalanche.

Debt markets qiUSDCn (native USDC) and qiUSDTn (USDt). Waits on the farm feed for LiquidateBorrow logs of those two
markets (one liquidation after a price move usually means others are under water) plus a ~60 s safety scan of the
accounts nearest to shortfall. For an account in shortfall it simulates the exact executor call
(Aave flashLoanSimple -> liquidateBorrow -> redeem -> UniV3 path -> repay with premium -> gain in USDC) and, in live
mode, sends it when the simulated gross is above the signed gas cap. A lost attempt costs gas only.
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

COMPTROLLER = '0x486af39519b4dc9a7fccd318217352830e8ad9b4'  # Benqi core comptroller (DefiLlama benqi adapter)
FLASH = '0x794a61358d6845594f94dc1db02a252b5b4814ad'        # Aave v3 Pool (Avalanche): flashLoanSimple lender
ROUTER = '0xbb00ff08d01d300023c629e8ffffcb65a5a578ce'       # Uniswap V3 SwapRouter02 (Avalanche)
MULTICALL = '0xca11bde05977b3631167028862be2a173976ca11'
WAVAX = '0xb31f66aa3c1e785363f0875a1b74e27b85fd66c7'
WETH = '0x49d5c2bdffac6ce2bfdb6640f4f80f226bc10bab'         # WETH.e
BTCB = '0x152b9d0fdc40c096757f570a51e494bd4b943e50'         # BTC.b
USDC = '0xb97ef9ef8734c71904d8002f8b6bc66dd9c48a6e'         # native USDC: the payout token
USDT = '0x9702230a8ea53601f5cd2dc00fdbc13d4df4a8c7'         # USDt
QI_AVAX = '0x5c0401e81bc07ca70fad469b451682c0d747ef1c'
QI_BTCB = '0x89a415b3d20098e6a6c8f7a59001c67bd3129821'
QI_ETH = '0x334ad834cd4481bb02d09615e7c11a00579a7909'
QI_USDC = '0xb715808a78f6041e46d61cb123c9b4a27056ae9c'      # qiUSDCn
QI_USDT = '0xd8fcda6ec4bdc547c0827b8804e89acd817d56ef'      # qiUSDTn
DEBTS = ((QI_USDC, USDC), (QI_USDT, USDT))                 # both have 6 decimals
# (qi market, underlying or wrapped native, redeems to native, UniV3 route to USDC as [token, fee, token, ...])
COLLS = (
    (QI_AVAX, WAVAX, True, [WAVAX, 500, USDC]),
    (QI_BTCB, BTCB, False, [BTCB, 500, USDC]),
    (QI_ETH, WETH, False, [WETH, 500, WAVAX, 500, USDC]),
    (QI_USDT, USDT, False, [USDT, 100, USDC]),
    (QI_USDC, USDC, False, [USDC]),
)
# Share of the stored borrow offered as repayment, largest first. The close factor is 0.5; a repayment above it or
# a seize above the borrower's collateral in that market makes the market refuse (MarketError(1, code)), so
# smaller sizes follow. The gain rises, then falls with size once swap slippage passes the 7 pct bonus:
# the sweep stops at the first size that gains less than the one before.
REPAY_SHARES = (0.5, 0.25, 0.12, 0.06)
SWEEP_MIN_USD = 2000                 # debts under this get only the first two sizes
MARKET_ERROR = 'e435995b'            # MarketError(uint256,uint256), cast sig
LIQ_TOPIC = '0x298637f684da70674f26509b10f07ec2fbc77a335ab1e7d6215a4b2484d8bb52'     # LiquidateBorrow, cast keccak
BORROW_TOPIC = '0x13ed6866d4e1ee6da46f845c46d7e54120883d75c5ea9a2dacc1c4ca8984ab80'  # Borrow, cast keccak
SEL_LIQUIDATE = '0x875f7da1'  # liquidate(address,(address,address,address,address,address,bool,address,bytes,address,bytes),uint256,uint256)

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
MAX_FEE_WEI = 2_000 * 10**9  # absolute ceiling for maxFeePerGas (the USD cap binds first)
MIN_TIP_WEI = 1            # Avalanche has no minimum tip; a bid of zero is not sent
BID_SHARE = 0.50           # priority fee bid: at most this share of the simulated gross
MAX_REPAY = 60_000_000_000  # 60,000 USDC / USDt, flash-loaned, never the bot's own funds
MIN_DEBT = 5_000_000       # skip accounts with less than 5 USD of in-scope debt
RELAY_CU_CAP = 75_000      # per UTC day; the feed's own CU is metered separately

NEAR_COUNT = 100
SCAN_INTERVAL = 3600
POLL_INTERVAL = 50         # two 27 s feed waits per loop: the safety cadence is ~55-60 s
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


def call(to, data, block='latest'):
    return rpc('eth_call', [{'to': to, 'data': data}, block])


def aggregate(calls, block='latest'):
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
    h = call(MULTICALL, enc, block)[2:]
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


def load_state():
    if STATE.exists():
        try:
            return json.loads(STATE.read_text())
        except Exception:
            pass
    return {'users': SEED, 'near': [], 'debt': {}, 'cursor_block': None, 'feed_cursor': {},
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


def native_price_usd():
    oracle = '0x' + call(COMPTROLLER, '0x7dc0d1d0')[-40:]              # oracle()
    return at(call(oracle, '0xfc57d4df' + aword(QI_AVAX)), 0) / 1e18   # getUnderlyingPrice(qiAVAX): USD per AVAX


def path_hex(parts):
    """[tokenA, fee, tokenB, ...] -> UniV3 packed path (hex, no 0x); a single token means no swap."""
    if len(parts) < 3:
        return ''
    return ''.join(format(p, '06x') if isinstance(p, int) else p[2:].lower() for p in parts)


def routes(debt, coll_route):
    """UniV3 paths (collateral -> debt, debt -> USDC) for a collateral whose route to USDC is coll_route."""
    if debt == USDC:
        return path_hex(coll_route), ''
    # debt is USDt: collateral -> USDC -> USDt, and the surplus USDt -> USDC at the end
    if coll_route[0] == USDT:
        return '', path_hex([USDT, 100, USDC])
    return path_hex(coll_route + [100, USDT]), path_hex([USDT, 100, USDC])


def calldata(user, qi_debt, debt, coll, repay, min_profit):
    qi_coll, underlying, is_native, coll_route = coll
    p_in, p_out = routes(debt, coll_route)

    def padded(p):
        return p.ljust(((len(p) + 63) // 64) * 64, '0')

    off_in = 10 * 32
    off_out = off_in + 32 + len(padded(p_in)) // 2
    job = (aword(qi_debt) + aword(qi_coll) + aword(user) + aword(debt) + aword(underlying) + word(int(is_native))
           + aword(ROUTER) + word(off_in) + aword(USDC) + word(off_out)
           + word(len(p_in) // 2) + padded(p_in) + word(len(p_out) // 2) + padded(p_out))
    return SEL_LIQUIDATE + aword(FLASH) + word(0x80) + word(repay) + word(min_profit) + job


def exec_ctx():
    if MODE == 'live':
        return bot_address(), EXEC, None
    return PAPER_OWNER, PAPER_EXEC, {PAPER_EXEC: {'code': RUNTIME}}


def sim(data, ctx, block='latest'):
    frm, to, ov = ctx
    params = [{'from': frm, 'to': to, 'data': data, 'gas': hex(3_000_000)}, block] + ([ov] if ov else [])
    return at(rpc('eth_call', params), 0)


def estimate(data, ctx):
    frm, to, ov = ctx
    params = [{'from': frm, 'to': to, 'data': data}, 'latest'] + ([ov] if ov else [])
    return int(rpc('eth_estimateGas', params), 16)


def winner_block(qi_debt, user, send_block, our_hash):
    """Block of the LiquidateBorrow that took this user near our send (ours if we won)."""
    head = int(rpc('eth_blockNumber', []), 16)
    logs = rpc('eth_getLogs', [{'address': qi_debt, 'fromBlock': hex(max(0, send_block - 300)), 'toBlock': hex(head),
                                'topics': [LIQ_TOPIC]}])
    logs = [x for x in logs if x['data'][2:][64 + 24:128].lower() == user[2:].lower()]   # word 1 = borrower
    ours = [int(x['blockNumber'], 16) for x in logs if x['transactionHash'].lower() == our_hash.lower()]
    if ours:
        return min(ours), None
    if not logs:
        return None, None
    first = min(logs, key=lambda x: int(x['blockNumber'], 16))
    return int(first['blockNumber'], 16), first['transactionHash']


def send_live(user, qi_debt, qi_coll, data, gas_limit, max_fee, priority, gross_usd, gas_cap_usd):
    import farmbot_signer
    reply = farmbot_signer.send(CHAIN, EXEC, data, 0, gas_limit, max_fee, max_priority_fee_per_gas=priority)
    h = None
    if isinstance(reply, dict):
        h = reply.get('txHash') or reply.get('tx_hash') or reply.get('hash')
    if not h:
        log('signer_reject', user=user, debt_market=qi_debt, coll_market=qi_coll, reply=reply)  # final, never retried
        return
    log('send', hash=h, user=user, debt_market=qi_debt, coll_market=qi_coll, gas_limit=gas_limit, max_fee=max_fee,
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
        wb, wtx = winner_block(qi_debt, user, b, h)
    except Exception:
        wb, wtx = None, None
    log('send_result', hash=h, user=user, debt_market=qi_debt, coll_market=qi_coll, result='won' if status else 'lost',
        gas_used=used, gas_cost_wei=cost, send_block=b, winner_block=wb, winner_tx=wtx,
        blocks_after_winner=(b - wb if wb is not None else None), gross_usd=gross_usd)


def positions(user, block='latest'):
    """In-scope borrows and collateral qiToken balances of one account, one Multicall."""
    calls = [(qi, '0x95dd9193' + aword(user)) for qi, _ in DEBTS]          # borrowBalanceStored(address)
    calls += [(c[0], '0x70a08231' + aword(user)) for c in COLLS]            # balanceOf(address)
    res = [at(d, 0) if ok and len(d) >= 66 else 0 for ok, d in aggregate(calls, block)]
    borrows = [(DEBTS[i][0], DEBTS[i][1], res[i]) for i in range(len(DEBTS)) if res[i] >= MIN_DEBT]
    colls = [COLLS[i] for i in range(len(COLLS)) if res[len(DEBTS) + i] > 0]
    return sorted(borrows, key=lambda z: -z[2]), colls


def best_route(user, shortfall, ctx, block='latest'):
    """Sweep debt market x collateral market x size by simulation. Returns (gain, qi_debt, debt, coll, repay) or None."""
    borrows, colls = positions(user, block)
    if not borrows or not colls:
        log('opportunity_skip', user=user, shortfall_usd=shortfall, reason='unsupported_assets')
        return None
    best = None
    for qi_debt, debt, borrow in borrows:
        shares = REPAY_SHARES if borrow / 1e6 >= SWEEP_MIN_USD else REPAY_SHARES[:2]
        for coll in colls:
            prev = None
            for share in shares:
                repay = min(int(borrow * share), MAX_REPAY)
                try:
                    gain = sim(calldata(user, qi_debt, debt, coll, repay, 0), ctx, block)
                except ReadBudgetExceeded:
                    raise
                except Exception as e:
                    log('simulate_revert', user=user, debt_market=qi_debt, coll_market=coll[0], repay=repay,
                        shortfall_usd=shortfall, error=str(e)[:200])
                    continue    # market refusal (seize above this collateral, account healthy) or swap failure
                if best is None or gain > best[0]:
                    best = (gain, qi_debt, debt, coll, repay)
                if prev is not None and gain <= prev:
                    break       # past the peak: the gain now falls with the size
                prev = gain
    return best


def attempt(s, user, shortfall, trigger):
    now = time.time()
    if s['cooldown'].get(user, 0) > now:
        return
    s['cooldown'][user] = now + 600
    avax_usd = native_price_usd()
    if avax_usd <= 0:
        return
    ctx = exec_ctx()
    best = best_route(user, shortfall, ctx)
    if best is None:
        return
    gain, qi_debt, debt, coll, repay = best
    gross_usd = gain / 1e6   # the gain is always native USDC (6 decimals)
    try:
        gas_limit = estimate(calldata(user, qi_debt, debt, coll, repay, 0), ctx) * 5 // 4
        base_price = int(rpc('eth_gasPrice', []), 16)
    except ReadBudgetExceeded:
        raise
    except Exception as e:
        log('simulate_revert', user=user, debt_market=qi_debt, coll_market=coll[0], error='estimate: ' + str(e)[:140])
        return
    # Fee ceiling so that maxFeePerGas x gasLimit < MAX_TX_USD (and never above MAX_FEE_WEI).
    # eth_gasPrice = base fee + a suggested tip, so 2 x base_price leaves room for base-fee growth.
    fee_ceiling = min(MAX_FEE_WEI, int(MAX_TX_USD * 0.98 / avax_usd * 1e18 / gas_limit))
    priority = int(gross_usd * BID_SHARE / avax_usd * 1e18 / gas_limit)       # bid <= BID_SHARE of gross
    priority = min(priority, fee_ceiling - 2 * base_price)
    if priority < MIN_TIP_WEI:
        log('opportunity_skip', user=user, debt_market=qi_debt, coll_market=coll[0], shortfall_usd=shortfall,
            gross_usd=gross_usd, reason='bid_under_min_tip', trigger=trigger)   # no room for a tip under the ceiling
        return
    max_fee = min(fee_ceiling, 2 * base_price + priority)
    gas_cap_usd = gas_limit * max_fee / 1e18 * avax_usd
    if max_fee < base_price + priority or gas_cap_usd >= MAX_TX_USD or gross_usd <= gas_cap_usd:
        log('opportunity_skip', user=user, debt_market=qi_debt, coll_market=coll[0], shortfall_usd=shortfall,
            gross_usd=gross_usd, gas_cap_usd=gas_cap_usd, reason='gross_not_above_gas_cap', trigger=trigger)
        return
    # On-chain floor: the executor reverts unless the gain covers the signed gas cap.
    min_profit = int(gas_cap_usd * 1e6) + 1
    data = calldata(user, qi_debt, debt, coll, repay, min_profit)
    try:
        gain = sim(data, ctx)  # the exact bytes that would be sent
    except ReadBudgetExceeded:
        raise
    except Exception as e:
        log('simulate_revert', user=user, debt_market=qi_debt, coll_market=coll[0], error='final: ' + str(e)[:140])
        return
    log('opportunity', user=user, debt_market=qi_debt, coll_market=coll[0], shortfall_usd=shortfall, repay=repay,
        gross_usd=gross_usd, gas_cap_usd=gas_cap_usd, gas_limit=gas_limit, max_fee=max_fee, priority=priority,
        min_profit=min_profit, simulated_gain=gain, trigger=trigger, mode=MODE)
    if MODE == 'live':
        send_live(user, qi_debt, coll[0], data, gas_limit, max_fee, priority, gross_usd, gas_cap_usd)
    else:
        log('paper_sim', user=user, debt_market=qi_debt, coll_market=coll[0], result='success', gain=gain,
            gross_usd=gross_usd)


def liquidity_of(users):
    """comptroller.getAccountLiquidity for each user -> [(liquidity_usd, shortfall_usd)], Multicalls of 100."""
    out = []
    for off in range(0, len(users), 100):
        batch = users[off:off + 100]
        res = aggregate([(COMPTROLLER, '0x5ec88c79' + aword(a)) for a in batch])
        for ok, d in res:
            out.append((at(d, 1) / 1e18, at(d, 2) / 1e18) if ok and len(d) >= 2 + 3 * 64 and at(d, 0) == 0 else (None, None))
    return out


def scan_full(s):
    """Hourly: in-scope debt of every known account, then liquidity of the debtors; keeps the nearest NEAR_COUNT."""
    users = s['users']
    debt = {}
    for off in range(0, len(users), 200):
        batch = users[off:off + 200]
        try:
            res = aggregate([(qi, '0x95dd9193' + aword(a)) for a in batch for qi, _ in DEBTS])
        except ReadBudgetExceeded:
            raise
        except Exception as e:
            log('scan_error', label='full_debt', offset=off, error=str(e)[:200])
            continue
        for i, a in enumerate(batch):
            total = sum(at(d, 0) if ok and len(d) >= 66 else 0 for ok, d in res[i * len(DEBTS):(i + 1) * len(DEBTS)])
            if total >= MIN_DEBT:
                debt[a] = total
    debtors = sorted(debt)
    try:
        liq = liquidity_of(debtors)
    except ReadBudgetExceeded:
        raise
    except Exception as e:
        log('scan_error', label='full_liquidity', error=str(e)[:200])
        return
    ranked, eligible = [], []
    for a, (free, short) in zip(debtors, liq):
        if free is None:
            continue
        if short > 0:
            eligible.append((debt[a], short, a))
        ranked.append(((free - short) * 1e6 / debt[a], a))   # free liquidity per USD of in-scope debt
    ranked.sort()
    s['near'] = [a for _, a in ranked[:NEAR_COUNT]]
    s['debt'] = {a: debt[a] for a in s['near']}
    log('scan', label='full', checked=len(users), debtors=len(debtors), underwater=len(eligible), near=len(s['near']))
    for d, short, a in sorted(eligible, reverse=True)[:3]:   # largest debt first
        attempt(s, a, short, 'full')


def scan_near(s, label):
    near = s['near'][:NEAR_COUNT + 50]
    if not near:
        return
    try:
        liq = liquidity_of(near)
    except ReadBudgetExceeded:
        raise
    except Exception as e:
        log('scan_error', label=label, error=str(e)[:200])
        return
    eligible = [(s['debt'].get(a, 0), short, a) for a, (free, short) in zip(near, liq) if short]
    log('scan', label=label, checked=len(near), underwater=len(eligible))
    for d, short, a in sorted(eligible, reverse=True)[:3]:
        attempt(s, a, short, label)


def discover(s):
    head = int(rpc('eth_blockNumber', []), 16) - 5   # the log provider can be a few blocks behind the head
    start = s['cursor_block'] + 1 if s['cursor_block'] is not None else head - 3000
    start = max(start, head - 3000)   # at most ~50 min of 1 s blocks per request
    if start > head:
        return
    logs = rpc('eth_getLogs', [{'address': [qi for qi, _ in DEBTS], 'fromBlock': hex(start), 'toBlock': hex(head),
                                'topics': [BORROW_TOPIC]}])
    users = set(s['users'])
    fresh = {'0x' + lg['data'][2:][24:64].lower() for lg in logs} - users   # Borrow data word 0 = borrower
    s['users'] = sorted(users | fresh)
    s['near'] = list(dict.fromkeys(s['near'] + sorted(fresh)))[:NEAR_COUNT + 50]  # new borrowers watched until the next full scan
    s['cursor_block'] = head
    log('discover', from_block=start, to_block=head, logs=len(logs), added=len(fresh), universe=len(s['users']))


def feed_wait(address, cursor):
    q = {'address': address, 'topic0': LIQ_TOPIC, 'timeout': '27'}
    if cursor:
        q['after'] = cursor
    with urllib.request.urlopen(FEED + '?' + urllib.parse.urlencode(q), timeout=40) as r:
        return json.load(r)


def main():
    s = load_state()
    s.setdefault('feed_cursor', {})
    s.setdefault('debt', {})
    avax_usd = native_price_usd()
    log('start', mode=MODE, executor=(EXEC if MODE == 'live' else PAPER_EXEC), universe=len(s['users']),
        avax_usd=avax_usd)
    while True:
        now = time.time()
        try:
            if now - s['last_discover'] >= DISCOVER_INTERVAL:
                s['last_discover'] = now
                discover(s)
            if now - s['last_scan'] >= SCAN_INTERVAL:
                s['last_scan'] = now
                s['last_poll'] = now
                scan_full(s)
            elif now - s['last_poll'] >= POLL_INTERVAL:
                s['last_poll'] = now
                scan_near(s, 'near')
            save_state(s)
            for qi, _ in DEBTS:   # two feed filters, one 27 s long-poll each
                result = feed_wait(qi, s['feed_cursor'].get(qi))
                s['feed_cursor'][qi] = result.get('cursor', s['feed_cursor'].get(qi))
                logs = result.get('logs') or []
                if result.get('gap') or any(x.get('removed') for x in logs):
                    scan_near(s, 'gap')
                elif logs:
                    log('feed', market=qi, events=len(logs), blocks=[x.get('blockNumber') for x in logs][:10])
                    scan_near(s, 'liquidation_feed')
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
            log('feed_error', error=str(e)[:180])   # 429/503/timeout: fall back to a state re-read
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
