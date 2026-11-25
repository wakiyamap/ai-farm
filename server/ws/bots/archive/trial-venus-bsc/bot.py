#!/usr/bin/env python3
"""trial-venus-bsc: cheap-chain trial of Venus core-pool liquidations on BNB Smart Chain.

Debt markets vUSDT and vUSDC. Waits on the farm feed for LiquidateBorrowedTokens logs of the Venus Liquidator
(one liquidation after a price move usually means others are under water) plus a ~60 s safety scan of the accounts
nearest to shortfall. For an account in shortfall it simulates the exact executor call
(Aave flashLoanSimple -> Venus Liquidator.liquidateBorrow -> vToken.redeem -> PancakeSwap V3 path -> repay with
premium -> gain in USDC) and, in live mode, sends it when the simulated gross is above the signed gas cap.
A lost attempt costs gas only.
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

# Venus addresses: VenusProtocol/venus-protocol deployments/bscmainnet_addresses.json
COMPTROLLER = '0xfd36e2c2a6789db23113685031d7f16329158384'  # Unitroller (core pool)
LIQUIDATOR = '0x0870793286aada55d39ce7f82fb2766e8004cf43'   # Venus Liquidator (comptroller.liquidatorContract())
FLASH = '0x6807dc923806fe8fd134338eabca509979a7e0cb'        # Aave v3 Pool (BNB chain): flashLoanSimple lender
ROUTER = '0x1b81d678ffb9c0263b24a97847620c99d213eb14'       # PancakeSwap V3 SwapRouter (struct with deadline)
MULTICALL = '0xca11bde05977b3631167028862be2a173976ca11'
WBNB = '0xbb4cdb9cbd36b01bd1cbaebf2de08d9173bc095c'
USDC = '0x8ac76a51cc950d9822d68b83fe1ad97b32cd580d'         # 18 decimals on BSC: the payout token
USDT = '0x55d398326f99059ff775485246999027b3197955'         # 18 decimals
BTCB = '0x7130d2a12b9bcbfae4f2634d864a1ee1ce3ead9c'
ETH = '0x2170ed0880ac9a755fd29b2688956bd959f933f8'
XRP = '0x1d2f0da169ceb9fc7b3144628db156f3f6c60dbe'
DOGE = '0xba2ae424d960c26247dd6c32edc70b295c744c43'
ADA = '0x3ee2200efb3400fabb9aacf31297cbdd1d435d47'
XVS = '0xcf6bb5389c92bdda8a3747ddb454cb7a64626c63'
SOL = '0x570a5d26f7765ecb712c0924e4de545b89fd43df'
CAKE = '0x0e09fabb73bd3ade0a17ecc321fd13a19e81ce82'
UNI = '0xbf5140a22578168fd562dccf235e5d43a02ce9b1'
LTC = '0x4338665cbb7b2485a8855a139b75d5e34ab0db94'
V_BNB = '0xa07c5b74c9b40447a954e1466938b865b6bbea36'
V_USDT = '0xfd5840cd36d94d7229439859c0112a4185bc0255'
V_USDC = '0xeca88125a5adbe82614ffc12d0db554e2e2867c8'
DEBTS = ((V_USDT, USDT), (V_USDC, USDC))                   # both have 18 decimals
# (vToken market, underlying or wrapped native, redeems to native, PancakeSwap V3 route to USDT as
# [token, fee, token, ...]). Routes measured 2026-11-18 (deepest pool per pair by quote balance); the three large
# collaterals appear twice, with the WBNB -> USDT hop at fee 100 and at fee 500: the simulation picks.
COLLS = (
    (V_BNB, WBNB, True, [WBNB, 100, USDT]),
    (V_BNB, WBNB, True, [WBNB, 500, USDT]),
    ('0x882c173bc7ff3b7786ca16dfed3dfffb9ee7847b', BTCB, False, [BTCB, 500, WBNB, 100, USDT]),
    ('0x882c173bc7ff3b7786ca16dfed3dfffb9ee7847b', BTCB, False, [BTCB, 500, WBNB, 500, USDT]),
    ('0xf508fcd89b8bd15579dc79a6827cb4686a3592c8', ETH, False, [ETH, 500, WBNB, 100, USDT]),
    ('0xf508fcd89b8bd15579dc79a6827cb4686a3592c8', ETH, False, [ETH, 500, WBNB, 500, USDT]),
    ('0xb248a295732e0225acd3337607cc01068e3b9c10', XRP, False, [XRP, 2500, WBNB, 100, USDT]),
    ('0xec3422ef92b2fb59e84c8b02ba73f1fe84ed8d71', DOGE, False, [DOGE, 2500, WBNB, 100, USDT]),
    ('0x9a0af7fdb2065ce470d72664de73cae409da28ec', ADA, False, [ADA, 2500, WBNB, 100, USDT]),
    ('0x151b1e2635a717bcdc836ecd6fbb62b674fe3e1d', XVS, False, [XVS, 2500, WBNB, 100, USDT]),
    ('0xbf515ba4d1b52ffdceabf20d31d705ce789f2cec', SOL, False, [SOL, 500, WBNB, 100, USDT]),
    ('0x86ac3974e2bd0d60825230fa6f355ff11409df5c', CAKE, False, [CAKE, 2500, WBNB, 100, USDT]),
    ('0x27ff564707786720c71a2e5c1490a63266683612', UNI, False, [UNI, 2500, WBNB, 100, USDT]),
    ('0x57a5297f2cb2c0aac9d554660acd6d385ab50c6b', LTC, False, [LTC, 500, WBNB, 100, USDT]),
    (V_USDC, USDC, False, [USDC, 100, USDT]),
    (V_USDT, USDT, False, [USDT]),
)
# Share of the stored borrow offered as repayment, largest first. The close factor is 0.5; a repayment above it or
# a seize above the borrower's collateral in that market makes Venus refuse (the Liquidator reverts
# LiquidationFailed), so smaller sizes follow. The gain rises, then falls with size once swap slippage passes the
# ~5 pct bonus: the sweep stops at the first size that gains less than the one before.
REPAY_SHARES = (0.5, 0.25, 0.12, 0.06)
SWEEP_MIN_USD = 2000                 # debts under this get only the first two sizes
LIQ_TOPIC = '0xdd091524d794aecdb5235b2d816620c2598790835e0f3849808504c2dcb4f1a9'     # LiquidateBorrowedTokens, cast keccak
BORROW_TOPIC = '0x13ed6866d4e1ee6da46f845c46d7e54120883d75c5ea9a2dacc1c4ca8984ab80'  # Borrow, cast keccak
# liquidate(address,(address,address,address,address,address,address,bool,address,bytes,address,bytes),uint256,uint256)
SEL_LIQUIDATE = '0x5365e244'

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
MAX_TX_USD = 0.90          # signed gas cap (gas price x gasLimit) stays under this
MAX_FEE_WEI = 3 * 10**9    # absolute ceiling for the gas price (the USD cap binds first)
BID_SHARE = 0.50           # gas price bid: at most this share of the simulated gross
MAX_REPAY = 60_000 * 10**18  # 60,000 USDT / USDC, flash-loaned, never the bot's own funds
MIN_DEBT = 20 * 10**18     # skip accounts with less than 20 USD of in-scope debt
RELAY_CU_CAP = 85_000      # per UTC day; the feed's own CU is metered separately

NEAR_COUNT = 50
SCAN_INTERVAL = 10800      # full scan every 3 h
POLL_INTERVAL = 55         # one 55 s feed wait per loop: the safety cadence is ~60 s
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
    return {'users': SEED, 'near': [], 'debt': {}, 'cursor_block': None, 'feed_cursor': None,
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
    return at(call(oracle, '0xfc57d4df' + aword(V_BNB)), 0) / 1e18     # getUnderlyingPrice(vBNB): USD per BNB


def path_hex(parts):
    """[tokenA, fee, tokenB, ...] -> V3 packed path (hex, no 0x); a single token means no swap."""
    if len(parts) < 3:
        return ''
    return ''.join(format(p, '06x') if isinstance(p, int) else p[2:].lower() for p in parts)


def routes(debt, coll_route):
    """V3 paths (collateral -> debt, debt -> USDC) for a collateral whose route to USDT is coll_route."""
    if debt == USDT:
        return path_hex(coll_route), path_hex([USDT, 100, USDC])
    # debt is USDC (the payout token): collateral -> USDT -> USDC, no exit swap
    if coll_route[0] == USDC:
        return '', ''
    return path_hex(coll_route + [100, USDC]), ''


def calldata(user, v_debt, debt, coll, repay, min_profit):
    v_coll, underlying, is_native, coll_route = coll
    p_in, p_out = routes(debt, coll_route)

    def padded(p):
        return p.ljust(((len(p) + 63) // 64) * 64, '0')

    off_in = 11 * 32
    off_out = off_in + 32 + len(padded(p_in)) // 2
    job = (aword(LIQUIDATOR) + aword(v_debt) + aword(v_coll) + aword(user) + aword(debt) + aword(underlying)
           + word(int(is_native)) + aword(ROUTER) + word(off_in) + aword(USDC) + word(off_out)
           + word(len(p_in) // 2) + padded(p_in) + word(len(p_out) // 2) + padded(p_out))
    return SEL_LIQUIDATE + aword(FLASH) + word(0x80) + word(repay) + word(min_profit) + job


def exec_ctx():
    if MODE == 'live':
        return bot_address(), EXEC, None
    return PAPER_OWNER, PAPER_EXEC, {PAPER_EXEC: {'code': RUNTIME}}


def sim(data, ctx, block='latest'):
    frm, to, ov = ctx
    params = [{'from': frm, 'to': to, 'data': data, 'gas': hex(8_000_000)}, block] + ([ov] if ov else [])
    return at(rpc('eth_call', params), 0)


def estimate(data, ctx):
    frm, to, ov = ctx
    params = [{'from': frm, 'to': to, 'data': data}, 'latest'] + ([ov] if ov else [])
    return int(rpc('eth_estimateGas', params), 16)


def winner_block(user, send_block, our_hash):
    """Block of the LiquidateBorrowedTokens that took this user near our send (ours if we won)."""
    head = int(rpc('eth_blockNumber', []), 16)
    logs = rpc('eth_getLogs', [{'address': LIQUIDATOR, 'fromBlock': hex(max(0, send_block - 600)),
                                'toBlock': hex(head), 'topics': [LIQ_TOPIC, None, '0x' + aword(user)]}])
    ours = [int(x['blockNumber'], 16) for x in logs if x['transactionHash'].lower() == our_hash.lower()]
    if ours:
        return min(ours), None
    if not logs:
        return None, None
    first = min(logs, key=lambda x: int(x['blockNumber'], 16))
    return int(first['blockNumber'], 16), first['transactionHash']


def send_live(user, v_debt, v_coll, data, gas_limit, gas_price, gross_usd, gas_cap_usd):
    import farmbot_signer
    reply = farmbot_signer.send(CHAIN, EXEC, data, 0, gas_limit, gas_price, max_priority_fee_per_gas=gas_price)
    h = None
    if isinstance(reply, dict):
        h = reply.get('txHash') or reply.get('tx_hash') or reply.get('hash')
    if not h:
        log('signer_reject', user=user, debt_market=v_debt, coll_market=v_coll, reply=reply)  # final, never retried
        return
    log('send', hash=h, user=user, debt_market=v_debt, coll_market=v_coll, gas_limit=gas_limit, max_fee=gas_price,
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
    log('send_result', hash=h, user=user, debt_market=v_debt, coll_market=v_coll, result='won' if status else 'lost',
        gas_used=used, gas_cost_wei=cost, send_block=b, winner_block=wb, winner_tx=wtx,
        blocks_after_winner=(b - wb if wb is not None else None), gross_usd=gross_usd)


def positions(user, block='latest'):
    """In-scope borrows and collateral vToken balances of one account, one Multicall."""
    markets = list(dict.fromkeys(c[0] for c in COLLS))
    calls = [(v, '0x95dd9193' + aword(user)) for v, _ in DEBTS]             # borrowBalanceStored(address)
    calls += [(m, '0x70a08231' + aword(user)) for m in markets]             # balanceOf(address)
    res = [at(d, 0) if ok and len(d) >= 66 else 0 for ok, d in aggregate(calls, block)]
    borrows = [(DEBTS[i][0], DEBTS[i][1], res[i]) for i in range(len(DEBTS)) if res[i] >= MIN_DEBT]
    held = {m for i, m in enumerate(markets) if res[len(DEBTS) + i] > 0}
    colls = [c for c in COLLS if c[0] in held]
    return sorted(borrows, key=lambda z: -z[2]), colls


def best_route(user, shortfall, ctx, block='latest'):
    """Sweep debt market x collateral route x size by simulation. Returns (gain, v_debt, debt, coll, repay) or None."""
    borrows, colls = positions(user, block)
    if not borrows or not colls:
        log('opportunity_skip', user=user, shortfall_usd=shortfall, reason='unsupported_assets')
        return None
    best = None
    for v_debt, debt, borrow in borrows:
        shares = REPAY_SHARES if borrow / 1e18 >= SWEEP_MIN_USD else REPAY_SHARES[:2]
        for coll in colls:
            prev = None
            for share in shares:
                repay = min(int(borrow * share), MAX_REPAY)
                try:
                    gain = sim(calldata(user, v_debt, debt, coll, repay, 0), ctx, block)
                except ReadBudgetExceeded:
                    raise
                except Exception as e:
                    log('simulate_revert', user=user, debt_market=v_debt, coll_market=coll[0], repay=repay,
                        shortfall_usd=shortfall, error=str(e)[:200])
                    continue    # Venus refusal (seize above this collateral, account healthy) or swap failure
                if best is None or gain > best[0]:
                    best = (gain, v_debt, debt, coll, repay)
                if prev is not None and gain <= prev:
                    break       # past the peak: the gain now falls with the size
                prev = gain
    return best


def attempt(s, user, shortfall, trigger):
    now = time.time()
    if s['cooldown'].get(user, 0) > now:
        return
    s['cooldown'][user] = now + 600
    bnb_usd = native_price_usd()
    if bnb_usd <= 0:
        return
    ctx = exec_ctx()
    best = best_route(user, shortfall, ctx)
    if best is None:
        return
    gain, v_debt, debt, coll, repay = best
    gross_usd = gain / 1e18   # the gain is always USDC (18 decimals on BSC)
    try:
        gas_limit = estimate(calldata(user, v_debt, debt, coll, repay, 0), ctx) * 5 // 4
        base_price = int(rpc('eth_gasPrice', []), 16)
    except ReadBudgetExceeded:
        raise
    except Exception as e:
        log('simulate_revert', user=user, debt_market=v_debt, coll_market=coll[0], error='estimate: ' + str(e)[:140])
        return
    # Price ceiling so that gasPrice x gasLimit < MAX_TX_USD (and never above MAX_FEE_WEI). BSC has no base fee:
    # the gas price is the whole bid, used as both maxFeePerGas and maxPriorityFeePerGas.
    fee_ceiling = min(MAX_FEE_WEI, int(MAX_TX_USD / bnb_usd * 1e18 / gas_limit) - 1)
    bid = int(gross_usd * BID_SHARE / bnb_usd * 1e18 / gas_limit)       # bid <= BID_SHARE of gross
    if base_price > bid:
        log('opportunity_skip', user=user, debt_market=v_debt, coll_market=coll[0], shortfall_usd=shortfall,
            gross_usd=gross_usd, minimum_gas_price=base_price, max_bid=bid,
            reason='minimum_gas_price_exceeds_bid_share', trigger=trigger)
        return
    gas_price = min(fee_ceiling, bid)
    gas_cap_usd = gas_limit * gas_price / 1e18 * bnb_usd
    if gas_price < base_price or gas_cap_usd >= MAX_TX_USD or gross_usd <= gas_cap_usd:
        log('opportunity_skip', user=user, debt_market=v_debt, coll_market=coll[0], shortfall_usd=shortfall,
            gross_usd=gross_usd, gas_cap_usd=gas_cap_usd, reason='gross_not_above_gas_cap', trigger=trigger)
        return
    # On-chain floor: the executor reverts unless the gain covers the signed gas cap.
    min_profit = int(gas_cap_usd * 1e18) + 1
    data = calldata(user, v_debt, debt, coll, repay, min_profit)
    try:
        gain = sim(data, ctx)  # the exact bytes that would be sent
    except ReadBudgetExceeded:
        raise
    except Exception as e:
        log('simulate_revert', user=user, debt_market=v_debt, coll_market=coll[0], error='final: ' + str(e)[:140])
        return
    log('opportunity', user=user, debt_market=v_debt, coll_market=coll[0], shortfall_usd=shortfall, repay=repay,
        gross_usd=gross_usd, gas_cap_usd=gas_cap_usd, gas_limit=gas_limit, max_fee=gas_price, priority=gas_price,
        min_profit=min_profit, simulated_gain=gain, trigger=trigger, mode=MODE)
    if MODE == 'live':
        send_live(user, v_debt, coll[0], data, gas_limit, gas_price, gross_usd, gas_cap_usd)
    else:
        log('paper_sim', user=user, debt_market=v_debt, coll_market=coll[0], result='success', gain=gain,
            gross_usd=gross_usd)


def liquidity_of(users):
    """comptroller.getAccountLiquidity for each user -> [(liquidity_usd, shortfall_usd)], Multicalls of 50."""
    out = []
    for off in range(0, len(users), 50):
        batch = users[off:off + 50]
        res = aggregate([(COMPTROLLER, '0x5ec88c79' + aword(a)) for a in batch])
        for ok, d in res:
            out.append((at(d, 1) / 1e18, at(d, 2) / 1e18) if ok and len(d) >= 2 + 3 * 64 and at(d, 0) == 0 else (None, None))
    return out


def scan_full(s):
    """Every 3 h: in-scope debt of every known account, then liquidity of the largest debtors; keeps the nearest NEAR_COUNT."""
    users = s['users']
    debt = {}
    for off in range(0, len(users), 200):
        batch = users[off:off + 200]
        try:
            res = aggregate([(v, '0x95dd9193' + aword(a)) for a in batch for v, _ in DEBTS])
        except ReadBudgetExceeded:
            raise
        except Exception as e:
            log('scan_error', label='full_debt', offset=off, error=str(e)[:200])
            continue
        for i, a in enumerate(batch):
            total = sum(at(d, 0) if ok and len(d) >= 66 else 0 for ok, d in res[i * len(DEBTS):(i + 1) * len(DEBTS)])
            if total >= MIN_DEBT:
                debt[a] = total
    debtors = sorted(debt, key=lambda a: -debt[a])[:1500]     # liquidity for the 1,500 largest debts only (read budget)
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
        ranked.append(((free - short) * 1e18 / debt[a], a))   # free liquidity per USD of in-scope debt
    ranked.sort()
    s['near'] = [a for _, a in ranked[:NEAR_COUNT]]
    s['debt'] = {a: debt[a] for a in s['near']}
    log('scan', label='full', checked=len(users), debtors=len(debt), ranked=len(debtors), underwater=len(eligible),
        near=len(s['near']))
    for d, short, a in sorted(eligible, reverse=True)[:3]:   # largest debt first
        attempt(s, a, short, 'full')


def scan_near(s, label):
    near = s['near'][:NEAR_COUNT]
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
    start = s['cursor_block'] + 1 if s['cursor_block'] is not None else head - 4000
    start = max(start, head - 4000)   # at most ~30 min of 0.45 s blocks per request (bsc ranges <= 5000)
    if start > head:
        return
    logs = rpc('eth_getLogs', [{'address': [v for v, _ in DEBTS], 'fromBlock': hex(start), 'toBlock': hex(head),
                                'topics': [BORROW_TOPIC]}])
    users = set(s['users'])
    fresh = {'0x' + lg['data'][2:][24:64].lower() for lg in logs} - users   # Borrow data word 0 = borrower
    s['users'] = sorted(users | fresh)
    s['cursor_block'] = head
    log('discover', from_block=start, to_block=head, logs=len(logs), added=len(fresh), universe=len(s['users']))


def feed_wait(cursor):
    q = {'address': LIQUIDATOR, 'topic0': LIQ_TOPIC, 'timeout': '55'}
    if cursor:
        q['after'] = cursor
    with urllib.request.urlopen(FEED + '?' + urllib.parse.urlencode(q), timeout=65) as r:
        return json.load(r)


def main():
    s = load_state()
    s.setdefault('feed_cursor', None)
    s.setdefault('debt', {})
    if set(SEED) - set(s['users']):   # a newer seed file adds to a saved universe and forces a full scan
        s['users'] = sorted(set(s['users']) | set(SEED))
        s['last_scan'] = 0
    bnb_usd = native_price_usd()
    log('start', mode=MODE, executor=(EXEC if MODE == 'live' else PAPER_EXEC), universe=len(s['users']),
        bnb_usd=bnb_usd)
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
            result = feed_wait(s.get('feed_cursor'))
            s['feed_cursor'] = result.get('cursor', s.get('feed_cursor'))
            logs = result.get('logs') or []
            if result.get('gap') or any(x.get('removed') for x in logs):
                s['last_poll'] = time.time()
                scan_near(s, 'gap')
            elif logs:
                log('feed', events=len(logs), blocks=[x.get('blockNumber') for x in logs][:10])
                s['last_poll'] = time.time()
                scan_near(s, 'liquidation_feed')
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
            log('feed_error', error=str(e)[:180])   # 429/503/timeout: the timed near scan re-reads the state
            time.sleep(POLL_INTERVAL)
        except ReadBudgetExceeded as e:
            log('read_budget', error=str(e))
            time.sleep(600)
        except Exception as e:
            log('loop_error', error=str(e)[:250])
            time.sleep(5)
        save_state(s)


if __name__ == '__main__':
    main()
