#!/usr/bin/env python3
"""trial-exactly-optimism: cheap-chain trial of Exactly Protocol (OP Mainnet) liquidations with USDC debt.

Exactly's Market.liquidate(borrower, maxAssets, seizeMarket) is open to anyone on OP Mainnet (no firewall, unlike
the Base deployment). The liquidator repays USDC debt and receives the seized collateral as the underlying token
with a 5 % incentive. Prices are plain Chainlink feeds read at call time, so an account becomes takeable in the
block of a Chainlink round (or by interest accrual).

The bot waits on the farm feed for AnswerUpdated of the Chainlink ETH/USD and OP/USD aggregators. On a lower
answer it re-reads the accounts close to the edge (Auditor.accountLiquidity) and simulates the exact executor
call (Morpho flash loan -> MarketUSDC.liquidate -> UniV3 swap -> repay) for the ones under water. Timed scans
cover everything else. In live mode it sends when the simulated gross > the signed gas cap. A lost attempt
costs gas only.
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
CHAIN = 'optimism'
FEED = 'http://127.0.0.1:8546/logs/optimism'

ZERO = '0x0000000000000000000000000000000000000000'
AUDITOR = '0xaeb62e6f27bc103702e7bc879ae98bcea56f027e'    # Exactly Auditor (exactly/protocol deployments/optimism)
EXA_USDC = '0x6926b434cce9b5b7966ae1bfeef6d0a7dcf3a8bb'   # MarketUSDC: the debt market this trial repays
EXA_WETH = '0xc4d4500326981eacd020e20a81b1c479c161c7ef'
EXA_OP = '0xa430a427bd00210506589906a71b54d6c256cedb'
EXA_WBTC = '0x6f748fd65d7c71949ba6641b3248c4c191f3b322'
EXA_USDCE = '0x81c9a7b55a4df39a9b7b5f781ec0e53539694873'
MORPHO = '0xce95afbb8ea029495c66020883f87aae8864af92'     # Morpho Blue (OP Mainnet), fee-free flash loans
ROUTER = '0x68b3465833fb72a70ecdf485e0e4c7bd8665fc45'     # Uniswap V3 SwapRouter02 (OP Mainnet)
MULTICALL = '0xca11bde05977b3631167028862be2a173976ca11'
WETH = '0x4200000000000000000000000000000000000006'
USDC = '0x0b2c639c533813f4aa9d7837caf62653d097ff85'
ETH_FEED_PROXY = '0x13e3ee699d1909e989722e753853ae30b17e08c5'   # Auditor.markets(exaWETH).priceFeed (Chainlink ETH/USD)
OP_FEED_PROXY = '0x0d276fc14719f9292d5c1ea2198673d1f4269246'    # Auditor.markets(exaOP).priceFeed (Chainlink OP/USD)
# Seize market -> (underlying, UniV3 fee tiers tried for underlying -> USDC). exaUSDC needs no swap.
# exawstETH is left out: no single-hop wstETH/USDC route was checked (2 of 115 captures in 7 d).
ROUTES = {
    EXA_WETH: (WETH, (500, 3000)),
    EXA_OP: ('0x4200000000000000000000000000000000000042', (3000,)),
    EXA_WBTC: ('0x68f180fcce6836688e9084f035309e29bf0a2095', (500, 3000)),
    EXA_USDCE: ('0x7f5c764cbc14f9669b88837ca1490cca17c31607', (100,)),
    EXA_USDC: (USDC, (0,)),
}
SEIZE_MARKETS = list(ROUTES)
LIQ_TOPIC = '0x67bb48f97d82192848c24158abf58ec614777328e19655e0a219652b773fd1db'      # Liquidate(address,address,uint256,uint256,address,uint256)
BORROW_TOPIC = '0x96558a334f4759f0e7c423d68c84721860bd8fbf94ddc4e55158ecb125ad04b5'   # Borrow(address,address,address,uint256,uint256)
BORROW_MAT_TOPIC = '0x66866b472f27d55d69496091bbd651907b2fb1041b3eeaca6e565ae5b5af4013'  # BorrowAtMaturity(uint256,address,address,address,uint256,uint256)
ANSWER_TOPIC = '0x0559884fd3a460db3073b7fc896cc77986f16e378210ded43186175bf646fc5f'   # AnswerUpdated(int256,uint256,uint256)
# liquidate(address,(address,address,address,address,address,address,uint24),uint256,uint256)
SEL_LIQUIDATE = '0x09dec4ee'
SEL_ACCOUNT_LIQ = '0x9e9d7967'    # accountLiquidity(address,address,uint256)
SEL_CHECK_LIQ = '0x216e7b58'      # checkLiquidation(address,address,address,uint256)
SEL_PREVIEW_DEBT = '0x1d43b30b'   # previewDebt(address)
SEL_ASSET_PRICE = '0xb883b058'    # assetPrice(address)
SEL_INCENTIVE = '0x8c765e94'      # liquidationIncentive()
SEL_AGGREGATOR = '0x245a7bfc'     # aggregator()
SEL_BALANCE = '0x70a08231'        # balanceOf(address)
MAXU = (1 << 256) - 1

PAPER_EXEC = '0xb464f7314d55ec6a9a0cf6f7f6df17af8ed5b352'   # fork deployment; paper code override only
PAPER_OWNER = '0xc0ffee0000000000000000000000000000000001'
EXEC = os.environ.get('EXECUTOR_ADDR_OPTIMISM') or os.environ.get('EXECUTOR_ADDR')
if MODE == 'live' and not EXEC:
    raise SystemExit('EXECUTOR_ADDR_OPTIMISM or EXECUTOR_ADDR is required in live mode')
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
MAX_TX_USD = 0.90            # signed gas cap (maxFeePerGas x gasLimit + L1 fee allowance) stays under this
L1_FEE_ALLOWANCE_USD = 0.02  # OP Mainnet L1 data fee for ~330 bytes of calldata, generous
MAX_FEE_WEI = 500_000_000    # 0.5 gwei absolute ceiling for maxFeePerGas
BID_SHARE = 0.50             # priority fee bid: at most this share of the simulated gross
MAX_REPAY = 20_000_000_000   # 20,000 USDC, flash-loaned, never the bot's own funds
MIN_DEBT = 1_000_000         # skip accounts with less than 1 USDC of exaUSDC debt
RELAY_CU_CAP = 65_000        # per UTC day; the feed's own CU is metered separately

NEAR_RATIO = 0.03            # near list: adjusted collateral under 1.03 x adjusted debt
ROUND_TRIES = 3              # at most this many accounts per price round
BATCH = 50                   # accounts per Multicall (2 sub-calls each)
SCAN_INTERVAL = 600          # safety poll of the USDC debtors, every 10 min
FULL_INTERVAL = 6 * 3600     # every known borrower (finds accounts that took USDC debt again)
DISCOVER_INTERVAL = 1800     # new borrowers from Borrow / BorrowAtMaturity logs, aggregator check
PARAM_TTL = 3600
MARKET_TTL = 600
CU_COST = {'eth_call': 26, 'eth_estimateGas': 20, 'eth_getLogs': 60, 'eth_getTransactionReceipt': 20,
           'eth_blockNumber': 10, 'eth_gasPrice': 20}
_id = 0
_params = {'ts': 0}
_market = {'ts': 0}          # base fee, ETH price and Morpho cash, re-read every MARKET_TTL


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


def account_data(users):
    """[(usdc_debt, adjusted_collateral_1e18, adjusted_debt_1e18)] per user; (0, 0, 0) when a sub-call failed."""
    calls = []
    for a in users:
        calls.append((AUDITOR, SEL_ACCOUNT_LIQ + aword(a) + word(0) + word(0)))
        calls.append((EXA_USDC, SEL_PREVIEW_DEBT + aword(a)))
    res = aggregate(calls)
    out = []
    for i in range(len(users)):
        (ok1, d1), (ok2, d2) = res[2 * i], res[2 * i + 1]
        if ok1 and ok2 and len(d1) >= 2 + 2 * 64 and len(d2) >= 2 + 64:
            out.append((at(d2, 0), at(d1, 0), at(d1, 1)))
        else:
            out.append((0, 0, 0))
    return out


def load_state():
    s = None
    if STATE.exists():
        try:
            s = json.loads(STATE.read_text())
        except Exception:
            s = None
    if not isinstance(s, dict):
        s = {}
    for k, v in (('users', SEED), ('debtors', []), ('near', []), ('cursor_block', None), ('feed_cursor', None),
                 ('last_scan', 0), ('last_full', 0), ('last_discover', 0), ('cooldown', {}), ('last_answer', {}),
                 ('aggregators', [])):
        s.setdefault(k, v)
    merged = sorted(set(s['users']) | set(SEED))   # a larger seed file is picked up on restart
    if len(merged) != len(s['users']):
        s['users'] = merged
        s['last_full'] = 0
    return s


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


def params():
    """Liquidation incentive (liquidator, lenders): re-read hourly."""
    if time.time() - _params['ts'] > PARAM_TTL:
        h = call(AUDITOR, SEL_INCENTIVE)
        liquidator, lenders = at(h, 0), at(h, 1)
        if not 0 < liquidator < 10**18 or lenders >= 10**17:
            raise RuntimeError('bad liquidation incentive')
        _params.update(ts=time.time(), liquidator=liquidator, lenders=lenders)
    return _params


def market():
    """(gas price wei, ETH/USD, Morpho USDC cash) at most MARKET_TTL old. The send keeps 2 x this base fee as
    headroom and the USD cap uses 1.15 x this ETH price."""
    if time.time() - _market['ts'] > MARKET_TTL:
        base_price = int(rpc('eth_gasPrice', []), 16)
        eth_usd = at(call(AUDITOR, SEL_ASSET_PRICE + aword(ETH_FEED_PROXY)), 0) / 1e18
        cash = at(call(USDC, SEL_BALANCE + aword(MORPHO)), 0)
        if eth_usd <= 0:
            raise RuntimeError('bad ETH price')
        _market.update(ts=time.time(), base_price=base_price, eth_usd=eth_usd, cash=cash)
    return _market['base_price'], _market['eth_usd'], _market['cash']


def seize_options(user, block='latest'):
    """[(max_repay_usdc, seize_market)] largest first: Auditor.checkLiquidation per seize market. It reverts
    (InsufficientShortfall) while the account is healthy, so an empty list means nothing to take."""
    res = aggregate([(AUDITOR, SEL_CHECK_LIQ + aword(EXA_USDC) + aword(m) + aword(user) + word(MAXU))
                     for m in SEIZE_MARKETS], block)
    out = [(at(d, 0), m) for m, (ok, d) in zip(SEIZE_MARKETS, res) if ok and len(d) >= 66 and at(d, 0) > 0]
    out.sort(reverse=True)
    return out


def calldata(user, seize, coll, fee, max_assets, min_profit):
    return (SEL_LIQUIDATE + aword(MORPHO) + aword(EXA_USDC) + aword(user) + aword(seize) + aword(USDC) + aword(coll)
            + aword(ROUTER) + word(fee) + word(max_assets) + word(min_profit))


def exec_ctx():
    if MODE == 'live':
        return bot_address(), EXEC, None
    return PAPER_OWNER, PAPER_EXEC, {PAPER_EXEC: {'code': RUNTIME}}


def sim(data, ctx, block='latest'):
    frm, to, ov = ctx
    p = [{'from': frm, 'to': to, 'data': data, 'gas': hex(4_000_000)}, block] + ([ov] if ov else [])
    return at(rpc('eth_call', p), 0)


def estimate(data, ctx):
    frm, to, ov = ctx
    p = [{'from': frm, 'to': to, 'data': data}, 'latest'] + ([ov] if ov else [])
    return int(rpc('eth_estimateGas', p), 16)


def winner_block(user, send_block, our_hash):
    """Block of the exaUSDC Liquidate that took this borrower near our send (ours if we won)."""
    head = int(rpc('eth_blockNumber', []), 16)
    # Liquidate(receiver indexed, borrower indexed, assets, lendersAssets, seizeMarket indexed, seizedAssets)
    logs = rpc('eth_getLogs', [{'address': EXA_USDC, 'fromBlock': hex(max(0, send_block - 60)), 'toBlock': hex(head),
                                'topics': [LIQ_TOPIC, None, '0x' + aword(user)]}])
    ours = [int(x['blockNumber'], 16) for x in logs if x['transactionHash'].lower() == our_hash.lower()]
    if ours:
        return min(ours), None
    if not logs:
        return None, None
    first = min(logs, key=lambda x: int(x['blockNumber'], 16))
    return int(first['blockNumber'], 16), first['transactionHash']


def send_live(user, seize, data, gas_limit, max_fee, priority, gross_usd, gas_cap_usd):
    import farmbot_signer
    reply = farmbot_signer.send(CHAIN, EXEC, data, 0, gas_limit, max_fee, max_priority_fee_per_gas=priority)
    h = None
    if isinstance(reply, dict):
        h = reply.get('txHash') or reply.get('tx_hash') or reply.get('hash')
    if not h:
        log('signer_reject', user=user, seize_market=seize, reply=reply)  # final, never retried
        return
    log('send', hash=h, user=user, seize_market=seize, gas_limit=gas_limit, max_fee=max_fee,
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
    cost = used * int(receipt['effectiveGasPrice'], 16) + int(receipt.get('l1Fee', '0x0'), 16)
    try:
        wb, wtx = winner_block(user, b, h)
    except Exception:
        wb, wtx = None, None
    log('send_result', hash=h, user=user, seize_market=seize, result='won' if status else 'lost',
        gas_used=used, gas_cost_wei=cost, send_block=b, winner_block=wb, winner_tx=wtx,
        blocks_after_winner=(b - wb if wb is not None else None), gross_usd=gross_usd)


def best_take(user, ctx, cash, block='latest'):
    """Simulate the executor call for the two largest seize markets, full and half size, every fee tier.
    Returns (gain, seize, coll, fee, max_assets) or None, plus the list of simulation errors."""
    p = params()
    errors = []
    best = None
    for max_repay, seize in seize_options(user, block)[:2]:
        coll, fees = ROUTES[seize]
        # maxAssets covers the repay plus the lenders' share (Auditor divides it by 1 + lenders); +2 for rounding
        top = min(max_repay * (10**18 + p['lenders']) // 10**18 + 2, MAX_REPAY, cash)
        for max_assets in dict.fromkeys((top, top // 2)):
            if max_assets < 200_000:
                continue
            for fee in fees:
                data = calldata(user, seize, coll, fee, max_assets, 0)
                try:
                    gain = sim(data, ctx, block)
                except ReadBudgetExceeded:
                    raise
                except Exception as e:
                    errors.append({'seize_market': seize, 'fee': fee, 'max_assets': max_assets, 'error': str(e)[:140]})
                    continue
                if best is None or gain > best[0]:
                    best = (gain, seize, coll, fee, max_assets)
    return best, errors


def attempt(s, user, debt, trigger):
    now = time.time()
    s['cooldown'][user] = now + 6 * 3600   # shortened below when there is something to take
    ctx = exec_ctx()
    base_price, eth_usd, cash = market()
    best, errors = best_take(user, ctx, cash)
    if best is None:
        if errors:
            log('simulate_revert', user=user, trigger=trigger, errors=errors[:4])
        else:
            s['cooldown'][user] = now + 20   # not under water at the price read now: retried on the next round
            log('round_no_take', user=user, trigger=trigger)
        return
    gain, seize, coll, fee, max_assets = best
    gross_usd = gain / 1e6
    try:
        gas_limit = estimate(calldata(user, seize, coll, fee, max_assets, 0), ctx) * 5 // 4
    except ReadBudgetExceeded:
        raise
    except Exception as e:
        log('simulate_revert', user=user, trigger=trigger,
            errors=[{'seize_market': seize, 'fee': fee, 'max_assets': max_assets, 'error': 'estimate: ' + str(e)[:140]}])
        return
    eth_usd *= 1.15   # margin over the oracle price: the signer values the cap with its own feed
    # Fee ceiling so that maxFeePerGas x gasLimit + L1 allowance < MAX_TX_USD (and never above 0.5 gwei).
    fee_ceiling = min(MAX_FEE_WEI, int((MAX_TX_USD - L1_FEE_ALLOWANCE_USD) / eth_usd * 1e18 / gas_limit))
    priority = int(gross_usd * BID_SHARE / eth_usd * 1e18 / gas_limit)       # bid <= BID_SHARE of gross
    priority = max(0, min(priority, fee_ceiling - 2 * base_price))
    max_fee = min(fee_ceiling, 2 * base_price + priority)
    gas_cap_usd = gas_limit * max_fee / 1e18 * eth_usd + L1_FEE_ALLOWANCE_USD
    if max_fee < base_price + priority or gas_cap_usd >= MAX_TX_USD or gross_usd <= gas_cap_usd:
        log('opportunity_skip', user=user, seize_market=seize, gross_usd=gross_usd, gas_cap_usd=gas_cap_usd,
            reason='gross_not_above_gas_cap', trigger=trigger)
        return
    # On-chain floor: the executor reverts unless the USDC gain covers the signed gas cap.
    min_profit = int(gas_cap_usd * 1e6) + 1
    data = calldata(user, seize, coll, fee, max_assets, min_profit)
    try:
        gain = sim(data, ctx)  # the exact bytes that would be sent
    except ReadBudgetExceeded:
        raise
    except Exception as e:
        log('simulate_revert', user=user, trigger=trigger,
            errors=[{'seize_market': seize, 'fee': fee, 'max_assets': max_assets, 'error': 'final: ' + str(e)[:140]}])
        return
    s['cooldown'][user] = now + 120   # a partial liquidation can leave more to take
    log('opportunity', user=user, seize_market=seize, collateral=coll, fee=fee, usdc_debt=debt, max_assets=max_assets,
        gross_usd=gross_usd, gas_cap_usd=gas_cap_usd, gas_limit=gas_limit, max_fee=max_fee, priority=priority,
        min_profit=min_profit, simulated_gain=gain, trigger=trigger, mode=MODE)
    if MODE == 'live':
        send_live(user, seize, data, gas_limit, max_fee, priority, gross_usd, gas_cap_usd)
    else:
        log('paper_sim', user=user, seize_market=seize, result='success', gain=gain, gross_usd=gross_usd)


def read_accounts(s, users, label):
    """[(usdc_debt, adjusted_collateral, adjusted_debt, user)] for exaUSDC debt >= MIN_DEBT."""
    rows = []
    for off in range(0, len(users), BATCH):
        batch = users[off:off + BATCH]
        try:
            data = account_data(batch)
        except ReadBudgetExceeded:
            raise
        except Exception as e:
            log('scan_error', label=label, offset=off, error=str(e)[:200])
            continue
        for a, (debt, coll, adj_debt) in zip(batch, data):
            if debt >= MIN_DEBT:
                rows.append((debt, coll, adj_debt, a))
    return rows


def run_attempts(s, rows, trigger):
    now = time.time()
    under = sorted((r for r in rows if r[1] < r[2]), reverse=True)   # largest USDC debt first
    picks = [r for r in under if s['cooldown'].get(r[3], 0) <= now][:ROUND_TRIES]
    for debt, coll, adj_debt, a in picks:
        try:
            attempt(s, a, debt, trigger)
        except ReadBudgetExceeded:
            raise
        except Exception as e:
            log('attempt_error', user=a, error=str(e)[:200])
    return len(under), len(picks)


def scan(s, label):
    """Safety poll. 'full' re-reads every known borrower, anything else the current USDC debtors."""
    users = s['users'] if label == 'full' or not s['debtors'] else s['debtors']
    rows = read_accounts(s, users, label)
    if users is s['users']:
        s['debtors'] = [r[3] for r in rows]
    # near list: closest to the edge first, read again on every lower price round
    near = sorted((r for r in rows if r[1] < r[2] * (1 + NEAR_RATIO)), key=lambda r: r[1] / max(r[2], 1))
    s['near'] = [r[3] for r in near[:BATCH]]
    under, tried = run_attempts(s, rows, label)
    log('scan', label=label, checked=len(users), debtors=len(rows), near=len(s['near']), underwater=under, tried=tried)


def on_round(s, logs):
    """New Chainlink ETH/USD or OP/USD round(s). A lower answer can put borrowers under water: re-read the near list."""
    down, last = False, None
    for lg in logs:
        t = lg.get('topics') or []
        if len(t) < 3:
            continue
        a = int(t[1], 16)
        a = a - (1 << 256) if a >> 255 else a
        feed = (lg.get('address') or '').lower()
        prev = s['last_answer'].get(feed)
        s['last_answer'][feed] = a
        if prev is None or a < prev:
            down = True
        last = lg
    if last is None:
        return
    lag = None
    try:
        ts = last.get('blockTimestamp')
        lag = round(time.time() - int(ts, 16), 2) if ts else None
    except Exception:
        pass
    if not down or not s['near']:
        log('round', block=last.get('blockNumber'), feed_lag_s=lag, action='up_or_flat' if not down else 'no_near_accounts')
        return
    rows = read_accounts(s, s['near'], 'round')
    under, tried = run_attempts(s, rows, 'round')
    log('round', block=last.get('blockNumber'), feed_lag_s=lag, action='down', near=len(s['near']), underwater=under,
        tried=tried)


def discover(s):
    head = int(rpc('eth_blockNumber', []), 16)
    start = s['cursor_block'] + 1 if s['cursor_block'] is not None else head - 3000
    start = max(start, head - 9000)   # at most 5 h of 2 s blocks per request
    if start > head:
        return
    logs = rpc('eth_getLogs', [{'address': EXA_USDC, 'fromBlock': hex(start), 'toBlock': hex(head),
                                'topics': [[BORROW_TOPIC, BORROW_MAT_TOPIC]]}])
    users = set(s['users'])
    fresh = set()
    for lg in logs:
        t = lg.get('topics') or []
        if len(t) >= 4:   # the borrower is the third indexed field in both events
            a = addr_of(t[3])
            if a not in users:
                fresh.add(a)
    s['users'] = sorted(users | fresh)
    s['debtors'] = list(dict.fromkeys(s['debtors'] + sorted(fresh)))
    s['cursor_block'] = head
    # a Chainlink proxy can be pointed at a new aggregator: the feed filter must follow it
    aggs = sorted(addr_of(call(p, SEL_AGGREGATOR)) for p in (ETH_FEED_PROXY, OP_FEED_PROXY))
    if all(int(a, 16) for a in aggs) and aggs != s.get('aggregators'):
        log('aggregators', old=s.get('aggregators'), new=aggs)
        s['aggregators'] = aggs
        s['feed_cursor'] = None
    market()
    log('discover', from_block=start, to_block=head, logs=len(logs), added=len(fresh), universe=len(s['users']))


def feed_wait(s):
    q = {'address': ','.join(s['aggregators']), 'topic0': ANSWER_TOPIC, 'timeout': '55'}
    if s.get('feed_cursor'):
        q['after'] = s['feed_cursor']
    with urllib.request.urlopen(FEED + '?' + urllib.parse.urlencode(q, safe=','), timeout=65) as r:
        return json.load(r)


def main():
    s = load_state()
    log('start', mode=MODE, executor=(EXEC if MODE == 'live' else PAPER_EXEC), universe=len(s['users']),
        incentive=params()['liquidator'] / 1e18)
    while True:
        now = time.time()
        try:
            if now - s['last_discover'] >= DISCOVER_INTERVAL or not s.get('aggregators'):
                s['last_discover'] = now
                discover(s)
            if now - s['last_full'] >= FULL_INTERVAL:
                s['last_full'] = s['last_scan'] = now
                scan(s, 'full')
            elif now - s['last_scan'] >= SCAN_INTERVAL:
                s['last_scan'] = now
                scan(s, 'debtors')
            save_state(s)
            result = feed_wait(s)
            s['feed_cursor'] = result.get('cursor', s.get('feed_cursor'))
            logs = result.get('logs') or []
            if result.get('gap') or any(x.get('removed') for x in logs):
                s['last_answer'] = {}
                s['last_scan'] = time.time()
                scan(s, 'gap')        # may have missed a round: re-read state through the relay
            elif logs:
                on_round(s, logs)
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
            log('feed_error', error=str(e)[:180])   # 429/503/timeout: fall back to a state re-read
            try:
                s['last_scan'] = time.time()
                scan(s, 'gap')
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
