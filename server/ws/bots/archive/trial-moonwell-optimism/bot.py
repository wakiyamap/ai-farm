#!/usr/bin/env python3
"""trial-moonwell-optimism: cheap-chain trial of Moonwell (OP Mainnet) liquidations with USDC debt.

Moonwell's OP Mainnet price feeds are ChainlinkOEVWrapper contracts: for 10 s after a new Chainlink round the
normal price read still returns the previous round, and only a liquidation sent through the collateral feed's
wrapper (updatePriceEarlyAndLiquidate, open to anyone) sees the new price; the wrapper keeps 70 % of the
liquidation bonus for the protocol. After the 10 s the plain mUSDC.liquidateBorrow opens with the full bonus.

The bot waits on the farm feed for AnswerUpdated of the Chainlink OP/USD aggregator. On a lower answer it
re-reads the mUSDC borrowers and simulates the exact executor call (Morpho flash loan -> wrapper
liquidation -> mOP.redeem -> UniV3 swap -> repay) for the ones close to the edge. Timed scans cover accounts
that are visibly under water (direct path). In live mode it sends when the simulated gross > the signed gas
cap. A lost attempt costs gas only.
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
COMPTROLLER = '0xca889f40aae37fff165bccf69aef1e82b5c511b9'  # Moonwell Comptroller (OP Mainnet), comptroller() of the mTokens
MUSDC = '0x8e08617b0d66359d73aa11e11017834c29155525'        # the debt market this trial repays
MWETH = '0xb4104c02bbf4e9be85aaa41a62974e4e28d59a33'
MOP = '0x9fc345a20541bf8773988515c5950ed69af01847'
MORPHO = '0xce95afbb8ea029495c66020883f87aae8864af92'       # Morpho Blue (OP Mainnet), fee-free flash loans
ROUTER = '0x68b3465833fb72a70ecdf485e0e4c7bd8665fc45'       # Uniswap V3 SwapRouter02 (OP Mainnet)
MULTICALL = '0xca11bde05977b3631167028862be2a173976ca11'
WETH = '0x4200000000000000000000000000000000000006'
USDC = '0x0b2c639c533813f4aa9d7837caf62653d097ff85'
OP_FEED_PROXY = '0x0d276fc14719f9292d5c1ea2198673d1f4269246'  # Chainlink OP/USD proxy = priceFeed() of the OP wrapper
# Collateral markets with a direct UniV3 pool to USDC holding > 6k USDC on 2026-11-17
# (scratch/trial-moonwell-optimism/prep.json, feeds.json):
# mToken -> (underlying, fee tiers tried, OEV wrapper of that collateral's feed). mUSDC needs no swap.
ROUTES = {
    MOP: ('0x4200000000000000000000000000000000000042', (3000,), '0xcf6b619f3ebf8fc52998431d1798cdaf9259fd28'),
    MWETH: (WETH, (500, 3000), '0xd7a07488d2024e577b23cc81e43dd8f43a67276b'),
    '0x6e6ca598a06e609c913551b729a228b023f06fdb': ('0x68f180fcce6836688e9084f035309e29bf0a2095', (500, 3000),
                                                   '0x16dd9fe1e075f262ddc3c1aa91920c8bd29edb42'),               # WBTC
    '0x3fe782c2fe7668c2f1eb313acf3022a31fead6b2': ('0xda10009cbd5d07dd0cecc66161fc93d7c9000da1', (100,), ZERO),  # DAI
    '0xa3a53899ee8f9f6e963437c5b3f805fec538bf84': ('0x94b008aa00579c1307b0ef2c499ad98a8ce58e58', (100,), ZERO),  # USDT
    MUSDC: (USDC, (0,), ZERO),
}
LIQ_TOPIC = '0x298637f684da70674f26509b10f07ec2fbc77a335ab1e7d6215a4b2484d8bb52'     # LiquidateBorrow(address,address,uint256,address,uint256)
BORROW_TOPIC = '0x13ed6866d4e1ee6da46f845c46d7e54120883d75c5ea9a2dacc1c4ca8984ab80'  # Borrow(address,uint256,uint256,uint256)
ANSWER_TOPIC = '0x0559884fd3a460db3073b7fc896cc77986f16e378210ded43186175bf646fc5f'  # AnswerUpdated(int256,uint256,uint256)
# liquidate(address,(address,address,address,address,address,address,uint24,address,address),uint256,uint256,bool)
SEL_LIQUIDATE = '0xc3c21a0e'
SEL_LIQUIDITY = '0x5ec88c79'      # getAccountLiquidity(address)
SEL_BORROW_BAL = '0x95dd9193'     # borrowBalanceStored(address)
SEL_ASSETS_IN = '0xabfceffc'      # getAssetsIn(address)
SEL_SNAPSHOT = '0xc37f68e2'       # getAccountSnapshot(address)
SEL_ORACLE = '0x7dc0d1d0'         # oracle()
SEL_PRICE = '0xfc57d4df'          # getUnderlyingPrice(address)
SEL_CLOSE = '0xe8755446'          # closeFactorMantissa()
SEL_INCENTIVE = '0x4ada90af'      # liquidationIncentiveMantissa()
SEL_AGGREGATOR = '0x245a7bfc'     # aggregator()

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
L1_FEE_ALLOWANCE_USD = 0.02  # OP Mainnet L1 data fee for ~500 bytes of calldata (measured 1e-7 ETH), generous
MAX_FEE_WEI = 500_000_000    # 0.5 gwei absolute ceiling for maxFeePerGas
BID_SHARE = 0.50             # priority fee bid: at most this share of the simulated gross
MAX_REPAY = 20_000_000_000   # 20,000 USDC, flash-loaned, never the bot's own funds
MIN_DEBT = 5_000_000         # skip accounts with less than 5 USDC of mUSDC debt
RELAY_CU_CAP = 65_000        # per UTC day; the feed's own CU is metered separately

NEAR_RATIO = 0.03            # round trigger: try accounts whose excess liquidity is under 3 % of their mUSDC debt
ROUND_TRIES = 3              # at most this many accounts per price round
BATCH = 100                  # accounts per Multicall (2 sub-calls each)
SCAN_INTERVAL = 300          # safety poll: every known mUSDC borrower, every 5 min
DISCOVER_INTERVAL = 600
PARAM_TTL = 3600
MARKET_TTL = 600
COLL_TTL = 6 * 3600
CU_COST = {'eth_call': 26, 'eth_estimateGas': 20, 'eth_getLogs': 60, 'eth_getTransactionReceipt': 20,
           'eth_blockNumber': 10, 'eth_gasPrice': 20}
_id = 0
_params = {'ts': 0}
_market = {'ts': 0}          # base fee and ETH price, re-read every MARKET_TTL so a round costs fewer calls


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


def aggregate(calls):
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
        out.append((ok, '0x' + h[start + off * 2 + 64:start + off * 2 + 64 + length * 2]))
    return out + [(False, '0x')] * (len(calls) - len(out))


def account_data(users):
    """[(debt_usdc, liquidity_1e18, shortfall_1e18)] per user; (0, 0, 0) when a sub-call failed."""
    calls = []
    for a in users:
        calls.append((COMPTROLLER, SEL_LIQUIDITY + aword(a)))
        calls.append((MUSDC, SEL_BORROW_BAL + aword(a)))
    res = aggregate(calls)
    out = []
    for i in range(len(users)):
        (ok1, d1), (ok2, d2) = res[2 * i], res[2 * i + 1]
        if ok1 and ok2 and len(d1) >= 2 + 3 * 64 and len(d2) >= 2 + 64 and at(d1, 0) == 0:
            out.append((at(d2, 0), at(d1, 1), at(d1, 2)))
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
    for k, v in (('users', SEED), ('debtors', []), ('cursor_block', None), ('feed_cursor', None), ('last_scan', 0),
                 ('last_discover', 0), ('cooldown', {}), ('coll', {}), ('last_answer', None), ('aggregator', None)):
        s.setdefault(k, v)
    return s


def save_state(s):
    now = time.time()
    s['cooldown'] = {k: v for k, v in s['cooldown'].items() if v > now}
    s['coll'] = {k: v for k, v in s['coll'].items() if v.get('ts', 0) + COLL_TTL > now}
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
    """Oracle address, close factor, liquidation incentive: re-read hourly."""
    if time.time() - _params['ts'] > PARAM_TTL:
        oracle = addr_of(call(COMPTROLLER, SEL_ORACLE))
        close = at(call(COMPTROLLER, SEL_CLOSE), 0)
        incentive = at(call(COMPTROLLER, SEL_INCENTIVE), 0)
        if int(oracle, 16) == 0 or not 0 < close <= 10**18 or incentive < 10**18:
            raise RuntimeError('bad comptroller parameters')
        _params.update(ts=time.time(), oracle=oracle, close=close, incentive=incentive)
    return _params


def market():
    """(gas price wei, ETH/USD) at most MARKET_TTL old. The send keeps 2 x this base fee as headroom and the
    USD cap uses 1.15 x this ETH price."""
    if time.time() - _market['ts'] > MARKET_TTL:
        base_price = int(rpc('eth_gasPrice', []), 16)
        eth_usd = price_raw(params()['oracle'], MWETH) / 1e18
        if eth_usd <= 0:
            raise RuntimeError('bad ETH price')
        _market.update(ts=time.time(), base_price=base_price, eth_usd=eth_usd)
    return _market['base_price'], _market['eth_usd']


def price_raw(oracle, mtoken):
    """Moonwell oracle price: USD x 1e(36 - underlying decimals)."""
    return at(call(oracle, SEL_PRICE + aword(mtoken)), 0)


def collateral_of(s, user):
    """[[value_usd, mToken], ...] of the user's supported collateral, largest first; cached for 6 h."""
    c = s['coll'].get(user)
    if c and c.get('ts', 0) + COLL_TTL > time.time():
        return c['markets']
    h = call(COMPTROLLER, SEL_ASSETS_IN + aword(user))
    n = at(h, 1)
    assets = [addr_of(h[2 + (2 + i) * 64:2 + (3 + i) * 64]) for i in range(min(n, 30))]
    markets = [m for m in assets if m in ROUTES]
    valued = []
    if markets:
        oracle = params()['oracle']
        snaps = aggregate([(m, SEL_SNAPSHOT + aword(user)) for m in markets])
        for m, (ok, d) in zip(markets, snaps):
            if not ok or len(d) < 2 + 4 * 64 or at(d, 0) != 0 or at(d, 1) == 0:
                continue
            underlying = at(d, 1) * at(d, 3) // 10**18                 # mToken balance x exchange rate
            value_usd = underlying * price_raw(oracle, m) / 1e36       # oracle price is USD x 1e(36 - decimals)
            if value_usd >= 1:
                valued.append([value_usd, m])
        valued.sort(reverse=True)
    s['coll'][user] = {'ts': time.time(), 'markets': valued}
    return valued


def calldata(user, mcoll, coll, fee, wrapper, repay, min_profit):
    return (SEL_LIQUIDATE + aword(MORPHO) + aword(MUSDC) + aword(user) + aword(mcoll) + aword(USDC) + aword(coll)
            + aword(ROUTER) + word(fee) + aword(WETH) + aword(wrapper) + word(repay) + word(min_profit) + word(0))


def exec_ctx():
    if MODE == 'live':
        return bot_address(), EXEC, None
    return PAPER_OWNER, PAPER_EXEC, {PAPER_EXEC: {'code': RUNTIME}}


def sim(data, ctx):
    frm, to, ov = ctx
    p = [{'from': frm, 'to': to, 'data': data, 'gas': hex(4_000_000)}, 'latest'] + ([ov] if ov else [])
    return at(rpc('eth_call', p), 0)


def estimate(data, ctx):
    frm, to, ov = ctx
    p = [{'from': frm, 'to': to, 'data': data}, 'latest'] + ([ov] if ov else [])
    return int(rpc('eth_estimateGas', p), 16)


def winner_block(user, send_block, our_hash):
    """Block of the mUSDC LiquidateBorrow that took this borrower near our send (ours if we won)."""
    head = int(rpc('eth_blockNumber', []), 16)
    logs = rpc('eth_getLogs', [{'address': MUSDC, 'fromBlock': hex(max(0, send_block - 60)), 'toBlock': hex(head),
                                'topics': [LIQ_TOPIC]}])
    # LiquidateBorrow has no indexed fields: data = liquidator, borrower, repayAmount, mTokenCollateral, seizeTokens
    logs = [x for x in logs if len(x.get('data', '')) >= 2 + 5 * 64 and addr_of(x['data'][2 + 64:2 + 128]) == user.lower()]
    ours = [int(x['blockNumber'], 16) for x in logs if x['transactionHash'].lower() == our_hash.lower()]
    if ours:
        return min(ours), None
    if not logs:
        return None, None
    first = min(logs, key=lambda x: int(x['blockNumber'], 16))
    return int(first['blockNumber'], 16), first['transactionHash']


def send_live(user, mcoll, path, data, gas_limit, max_fee, priority, gross_usd, gas_cap_usd):
    import farmbot_signer
    reply = farmbot_signer.send(CHAIN, EXEC, data, 0, gas_limit, max_fee, max_priority_fee_per_gas=priority)
    h = None
    if isinstance(reply, dict):
        h = reply.get('txHash') or reply.get('tx_hash') or reply.get('hash')
    if not h:
        log('signer_reject', user=user, collateral_market=mcoll, reply=reply)  # final, never retried
        return
    log('send', hash=h, user=user, collateral_market=mcoll, path=path, gas_limit=gas_limit, max_fee=max_fee,
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
    log('send_result', hash=h, user=user, collateral_market=mcoll, path=path, result='won' if status else 'lost',
        gas_used=used, gas_cost_wei=cost, send_block=b, winner_block=wb, winner_tx=wtx,
        blocks_after_winner=(b - wb if wb is not None else None), gross_usd=gross_usd)


def attempt(s, user, debt, shortfall, trigger, path):
    """path 'wrapper': liquidate through the collateral feed's OEV wrapper (sees the newest Chainlink round);
    path 'direct': plain mUSDC.liquidateBorrow (needs a shortfall at the price everyone reads)."""
    now = time.time()
    # direct: 6 h when nothing profitable (bad-debt dust); wrapper: retried on the next round
    s['cooldown'][user] = now + (6 * 3600 if path == 'direct' else 20)
    valued = collateral_of(s, user)
    if not valued:
        log('opportunity_skip', user=user, shortfall=shortfall, reason='no_supported_collateral', trigger=trigger)
        return
    p = params()
    ctx = exec_ctx()
    max_repay = min(debt * p['close'] // 10**18 * 999 // 1000, MAX_REPAY)
    best = None
    for value_usd, m in valued[:2]:
        coll, fees, wrapper = ROUTES[m]
        if path == 'wrapper':
            if m != MOP:
                continue   # the feed this bot waits on is OP/USD: only the OP wrapper has a fresh round to unlock
        else:
            wrapper = ZERO
        # the seize is repay x incentive at oracle prices and must fit in this collateral balance
        fit = int(value_usd * 1e6 * 10**18 / p['incentive'] * 0.98)
        top = min(max_repay, fit)
        # the half size can pay more (less swap slippage); under 100 USDC the difference is cents: one size only
        sizes = (top,) if path == 'wrapper' and top < 100_000_000 else (top, top // 2)
        for repay in dict.fromkeys(sizes):
            if repay < 1_000_000:
                continue
            for fee in fees:
                data = calldata(user, m, coll, fee, wrapper, repay, 0)
                try:
                    gain = sim(data, ctx)
                except ReadBudgetExceeded:
                    raise
                except Exception as e:
                    if path == 'direct':
                        log('simulate_revert', user=user, collateral_market=m, fee=fee, repay=repay, path=path,
                            error=str(e)[:160])
                    continue
                if best is None or gain > best[0]:
                    best = (gain, m, coll, fee, wrapper, repay)
    if best is None:
        if path == 'wrapper':
            log('round_no_take', user=user, trigger=trigger)   # not under water at the new round, or no profit
        return
    gain, m, coll, fee, wrapper, repay = best
    gross_usd = gain / 1e6
    try:
        gas_limit = estimate(calldata(user, m, coll, fee, wrapper, repay, 0), ctx) * 5 // 4
        base_price, eth_usd = market()
    except ReadBudgetExceeded:
        raise
    except Exception as e:
        log('simulate_revert', user=user, collateral_market=m, fee=fee, repay=repay, path=path,
            error='estimate: ' + str(e)[:140])
        return
    eth_usd *= 1.15   # margin over the oracle price: the signer values the cap with its own feed
    # Fee ceiling so that maxFeePerGas x gasLimit + L1 allowance < MAX_TX_USD (and never above 0.5 gwei).
    fee_ceiling = min(MAX_FEE_WEI, int((MAX_TX_USD - L1_FEE_ALLOWANCE_USD) / eth_usd * 1e18 / gas_limit))
    priority = int(gross_usd * BID_SHARE / eth_usd * 1e18 / gas_limit)       # bid <= BID_SHARE of gross
    priority = max(0, min(priority, fee_ceiling - 2 * base_price))
    max_fee = min(fee_ceiling, 2 * base_price + priority)
    gas_cap_usd = gas_limit * max_fee / 1e18 * eth_usd + L1_FEE_ALLOWANCE_USD
    if max_fee < base_price + priority or gas_cap_usd >= MAX_TX_USD or gross_usd <= gas_cap_usd:
        log('opportunity_skip', user=user, collateral_market=m, shortfall=shortfall, gross_usd=gross_usd,
            gas_cap_usd=gas_cap_usd, reason='gross_not_above_gas_cap', trigger=trigger, path=path)
        return
    # On-chain floor: the executor reverts unless the USDC gain covers the signed gas cap.
    min_profit = int(gas_cap_usd * 1e6) + 1
    data = calldata(user, m, coll, fee, wrapper, repay, min_profit)
    if path == 'direct':
        try:
            gain = sim(data, ctx)  # the exact bytes that would be sent
        except ReadBudgetExceeded:
            raise
        except Exception as e:
            log('simulate_revert', user=user, collateral_market=m, fee=fee, repay=repay, path=path,
                error='final: ' + str(e)[:140])
            return
    # wrapper path: the 10 s window is short, so the bytes differ from the simulated ones only in minProfit
    # (below the simulated gain by the check above); the executor enforces it on-chain either way.
    s['cooldown'][user] = now + 600
    log('opportunity', user=user, collateral_market=m, collateral=coll, fee=fee, path=path, wrapper=wrapper,
        shortfall=shortfall, repay=repay, gross_usd=gross_usd, gas_cap_usd=gas_cap_usd, gas_limit=gas_limit,
        max_fee=max_fee, priority=priority, min_profit=min_profit, simulated_gain=gain, trigger=trigger, mode=MODE)
    if MODE == 'live':
        send_live(user, m, path, data, gas_limit, max_fee, priority, gross_usd, gas_cap_usd)
    else:
        log('paper_sim', user=user, collateral_market=m, path=path, result='success', gain=gain, gross_usd=gross_usd)


def read_accounts(s, label):
    """Re-read every known borrower. Returns [(debt, liquidity, shortfall, user)] for debt >= MIN_DEBT."""
    rows = []
    users = s['users'] if label == 'full' else (s['debtors'] or s['users'])
    for off in range(0, len(users), BATCH):
        batch = users[off:off + BATCH]
        try:
            data = account_data(batch)
        except ReadBudgetExceeded:
            raise
        except Exception as e:
            log('scan_error', label=label, offset=off, error=str(e)[:200])
            continue
        for a, (debt, liq, short) in zip(batch, data):
            if debt >= MIN_DEBT:
                rows.append((debt, liq, short, a))
    if label == 'full':
        s['debtors'] = [r[3] for r in rows]
    return rows


def run_attempts(s, picks, trigger, path):
    for debt, liq, short, a in picks:
        try:
            attempt(s, a, debt, short / 1e18, trigger, path)
        except ReadBudgetExceeded:
            raise
        except Exception as e:
            log('attempt_error', user=a, path=path, error=str(e)[:200])


def scan(s, label):
    """Safety poll: accounts visibly under water are tried on the direct path."""
    rows = read_accounts(s, label)
    now = time.time()
    under = sorted((r for r in rows if r[2] > 0), reverse=True)   # largest debt first
    log('scan', label=label, checked=len(s['users']) if label == 'full' else len(s['debtors']), debtors=len(rows),
        underwater=len(under))
    run_attempts(s, [r for r in under if s['cooldown'].get(r[3], 0) <= now][:3], label, 'direct')
    # keep the collateral cache warm for accounts near the edge, so a price round needs 3 reads, not 8
    for debt, liq, short, a in rows:
        if liq / 1e18 <= NEAR_RATIO * debt / 1e6 and a not in s['coll']:
            try:
                collateral_of(s, a)
            except ReadBudgetExceeded:
                raise
            except Exception as e:
                log('scan_error', label='collateral', user=a, error=str(e)[:160])


def on_round(s, logs):
    """New Chainlink OP/USD round(s). A lower answer can put OP-collateral borrowers under water at the new
    price while everyone else still reads the previous round for 10 s: try them through the wrapper."""
    answers = []
    for lg in logs:
        t = lg.get('topics') or []
        if len(t) >= 3:
            a = int(t[1], 16)
            answers.append(a - (1 << 256) if a >> 255 else a)
    if not answers:
        return
    prev, new = s.get('last_answer'), answers[-1]
    s['last_answer'] = new
    block = logs[-1].get('blockNumber')
    ts = logs[-1].get('blockTimestamp')
    lag = None
    try:
        lag = round(time.time() - int(ts, 16), 2) if ts else None
    except Exception:
        pass
    if prev is not None and new >= prev:
        log('round', answer=new, prev=prev, block=block, feed_lag_s=lag, action='up_or_flat')
        return
    rows = read_accounts(s, 'debtors')
    now = time.time()
    # An account whose collateral is OP flips when its excess liquidity is below about debt x price drop
    # (collateral x factor ~ debt near the edge); 1.5 x for margin, never above NEAR_RATIO.
    drop = (prev - new) / prev if prev else NEAR_RATIO
    ratio = min(NEAR_RATIO, max(0.001, 1.5 * drop))
    # debt is USDC with 6 decimals, liquidity is USD x 1e18; closest to the edge relative to debt first
    near = sorted((r for r in rows if r[2] > 0 or r[1] / 1e18 <= ratio * r[0] / 1e6),
                  key=lambda r: (r[1] - r[2]) / r[0])
    near = [r for r in near if s['cooldown'].get(r[3], 0) <= now][:ROUND_TRIES]
    log('round', answer=new, prev=prev, block=block, feed_lag_s=lag, action='down', drop=round(drop, 6),
        debtors=len(rows), tried=len(near))
    run_attempts(s, near, 'round', 'wrapper')


def discover(s):
    head = int(rpc('eth_blockNumber', []), 16)
    start = s['cursor_block'] + 1 if s['cursor_block'] is not None else head - 3000
    start = max(start, head - 9000)   # at most 5 h of 2 s blocks per request
    if start > head:
        return
    logs = rpc('eth_getLogs', [{'address': MUSDC, 'fromBlock': hex(start), 'toBlock': hex(head),
                                'topics': [BORROW_TOPIC]}])
    users = set(s['users'])
    fresh = set()
    for lg in logs:
        d = lg.get('data', '')
        if len(d) >= 2 + 64:   # Borrow has no indexed fields: borrower is data word 0
            a = addr_of(d[2:2 + 64])
            if a not in users:
                fresh.add(a)
    s['users'] = sorted(users | fresh)
    s['debtors'] = list(dict.fromkeys(s['debtors'] + sorted(fresh)))
    s['cursor_block'] = head
    # the Chainlink proxy can be pointed at a new aggregator: the feed filter must follow it
    agg = addr_of(call(OP_FEED_PROXY, SEL_AGGREGATOR))
    if int(agg, 16) and agg != s.get('aggregator'):
        log('aggregator', old=s.get('aggregator'), new=agg)
        s['aggregator'] = agg
        s['feed_cursor'] = None
    market()
    log('discover', from_block=start, to_block=head, logs=len(logs), added=len(fresh), universe=len(s['users']))


def feed_wait(s):
    q = {'address': s['aggregator'], 'topic0': ANSWER_TOPIC, 'timeout': '55'}
    if s.get('feed_cursor'):
        q['after'] = s['feed_cursor']
    with urllib.request.urlopen(FEED + '?' + urllib.parse.urlencode(q), timeout=65) as r:
        return json.load(r)


def main():
    s = load_state()
    log('start', mode=MODE, executor=(EXEC if MODE == 'live' else PAPER_EXEC), universe=len(s['users']),
        oracle=params()['oracle'])
    while True:
        now = time.time()
        try:
            if now - s['last_discover'] >= DISCOVER_INTERVAL or not s.get('aggregator'):
                s['last_discover'] = now
                discover(s)
            if now - s['last_scan'] >= SCAN_INTERVAL:
                s['last_scan'] = now
                scan(s, 'full')
            save_state(s)
            result = feed_wait(s)
            s['feed_cursor'] = result.get('cursor', s.get('feed_cursor'))
            logs = result.get('logs') or []
            if result.get('gap') or any(x.get('removed') for x in logs):
                s['last_answer'] = None
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
