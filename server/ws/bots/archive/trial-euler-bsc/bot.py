#!/usr/bin/env python3
"""trial-euler-bsc: cheap-chain trial of Euler EVK liquidations on BNB Smart Chain (USDT, USDC or USD1 debt).

Waits on the farm feed for a Liquidate log of the eUSDT-6 vault (an unwind there comes in many tranches, and the
tranches the incumbents leave are what this bot can take), plus a ~110 s timed scan of the accounts nearest to
health 1. For an underwater account it simulates the exact executor call (V3 flash swap on the collateral/debt
pool -> EVC batch liquidate / repay / redeem -> sell the rest -> walk to USDC) at several sizes and, in live mode,
sends the best one when the simulated gross is above the signed gas cap. A lost attempt costs gas only.
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

MULTICALL = '0xca11bde05977b3631167028862be2a173976ca11'
EVC = '0xb2e5a73cee08593d1a076a2ae7a6e02925a640ea'        # vault.EVC() of every bsc EVK borrow vault (probe.json)
V3_FACTORY = '0x0bfbcf9fa4f9c56b0f40a671ad40e0805a091865'  # PancakeSwap V3 factory = SwapRouter 0x1b81d678.factory()
USDC = '0x8ac76a51cc950d9822d68b83fe1ad97b32cd580d'       # 18 decimals on BSC: the payout token
USDT = '0x55d398326f99059ff775485246999027b3197955'       # 18 decimals
USD1 = '0x8d0d000ee44948fc98c9b98a4fa4921476f08b0d'       # 18 decimals
P_USDT_USDC = '0x92b7807bf19b7dddf89b706143896d05228f3121'  # Pancake V3 USDT/USDC 0.01% (factory getPool, probe.json)
P_USD1_USDT = '0x9c4ee895e4f6ce07ada631c508d1306db7502cce'  # Pancake V3 USD1/USDT 0.01%
P_WBNB_USDT = '0x36696169c63e42cd08ce11f5deebbcebae652050'  # Pancake V3 USDT/WBNB 0.05%: BNB price (token0 = USDT)
# Debt asset -> pools that walk it to USDC after the liquidation (the profit always ends as USDC).
OUT_POOLS = {USDC: [], USDT: [P_USDT_USDC], USD1: [P_USD1_USDT, P_USDT_USDC]}
FEES = (100, 500, 2500, 10000)
FEED_VAULT = '0x95c5fd8618c68d6156a739c1eab5aa7c807ff148'  # eUSDT-6 (ASTER collateral): 9 of the 10 takes of the last 7 d
BORROW_TOPIC = '0xcbc04eca7e9da35cb1393a6135a199ca52e450d5e9251cbd99f7847d33a36750'   # Borrow(address,uint256)
LIQ_TOPIC = '0x8246cc71ab01533b5bebc672a636df812f10637ad720797319d5741d5ebb3962'      # Liquidate(address,address,address,uint256,uint256)
SEL_RUN = '0x1ca6881a'          # run((address,address,address,uint256,uint256,address,address[],address,uint256))
SEL_ACCOUNT_LIQUIDITY = '0xa824bf67'   # accountLiquidity(address,bool)
SEL_CHECK_LIQUIDATION = '0x88aa6f12'   # checkLiquidation(address,address,address)
SEL_GET_COLLATERALS = '0xa4d25d1e'     # getCollaterals(address)
SEL_ASSET = '0x38d52e0f'
SEL_SLOT0 = '0x3850c7bd'
SEL_GET_POOL = '0x1698ee82'            # getPool(address,address,uint24)
SEL_BALANCE_OF = '0x70a08231'
SEL_TRY_AGGREGATE = '0xbce38bd7'

PAPER_EXEC = '0x4e3ce6b0998d325e5ba2d1863b42b205c922c559'   # fork deployment; paper code override only
PAPER_OWNER = '0xc0ffee0000000000000000000000000000000004'  # the owner baked into that runtime
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
_seed = json.loads((HERE / 'seed-accounts.json').read_text())
SEED = _seed['positions']                    # [[debtVault, account], ...]
SEED_FROM_BLOCK = _seed.get('covered_from_block')   # Borrow logs from here to the seed's head are in SEED
DEBT_VAULTS = tuple(_seed['debt_vaults'])    # the 18 borrow vaults whose asset is USDT, USDC or USD1 (probe.json)
BLOCKS_PER_DAY = 191_700
BACKFILL_DAYS = 90
BACKFILL_PAGES = 3        # per discover round: 3 x 75 CU every 10 min until done (~1,900 pages over ~4.5 days, ~144,000 CU once)

# ---- loss guard -----------------------------------------------------------------------------
MAX_TX_USD = 0.90          # signed gas cap (gas price x gasLimit) stays under this
MAX_FEE_WEI = 3 * 10**9    # absolute ceiling for the gas price (the USD cap binds first)
BID_SHARE = 0.50           # gas price bid: at most this share of the simulated gross
MAX_REPAY = 100_000 * 10**18  # per call, sourced by the flash swap, never the bot's own funds
REPAY_SHARES = (1.0, 0.5, 0.25, 0.12, 0.06, 0.03, 0.015, 0.006, 0.002)   # pool depth decides which size pays
MIN_REPAY = 5 * 10**18     # do not simulate sizes under 5 units of the debt asset
MIN_LIABILITY = 5 * 10**18  # skip accounts with less than 5 USD of debt (unit of account USD, 18 decimals)
RELAY_CU_CAP = 90_000      # per UTC day; the feed's own CU is metered separately

NEAR_COUNT = 150
SCAN_INTERVAL = 3600
POLL_INTERVAL = 100        # with the 55 s feed wait the safety cadence is ~110 s; a Liquidate log scans at once
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


def addr_of(h):
    return '0x' + h[-40:].lower()


def call(to, data):
    return rpc('eth_call', [{'to': to, 'data': data}, 'latest'])


def aggregate(calls):
    """One Multicall3 tryAggregate(false, [(target, data)]). Returns [(ok, returndata hex)] per call."""
    starts, acc = [], 32 * len(calls)
    for _, data in calls:
        starts.append(acc)
        size = (len(data) - 2) // 2
        acc += 96 + ((size + 31) // 32) * 32
    enc = SEL_TRY_AGGREGATE + word(0) + word(64) + word(len(calls)) + ''.join(word(x) for x in starts)
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


def load_state():
    if STATE.exists():
        try:
            return json.loads(STATE.read_text())
        except Exception:
            pass
    return {'positions': SEED, 'near': [], 'cursor_block': None, 'feed_cursor': None, 'assets': {}, 'pools': {},
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
    """USDT per WBNB from the Pancake V3 USDT/WBNB 0.05% pool (token0 = USDT, token1 = WBNB, both 18 decimals)."""
    sqrt_p = at(call(P_WBNB_USDT, SEL_SLOT0), 0)
    if sqrt_p <= 0:
        return 0.0
    price = 1.0 / ((sqrt_p / 2**96) ** 2)
    return price if 50 < price < 20000 else 0.0   # outside this range the read is not a BNB price: do nothing


def calldata(vault, coll_vault, violator, repay, pool, out_pools, min_profit):
    # run(Params): the tuple holds a dynamic array, so it is encoded behind one offset word. Head = 9 words
    # (debtVault, collVault, violator, repayAssets, minYieldShares, pool, offset of outPools, payout, minProfit).
    return (SEL_RUN + word(32) + aword(vault) + aword(coll_vault) + aword(violator) + word(repay) + word(0)
            + aword(pool) + word(9 * 32) + aword(USDC) + word(min_profit)
            + word(len(out_pools)) + ''.join(aword(p) for p in out_pools))


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


def asset_of(s, vault):
    if vault not in s['assets']:
        s['assets'][vault] = addr_of(call(vault, SEL_ASSET))
    return s['assets'][vault]


def pools_for(s, coll_asset, debt_asset):
    """Pancake V3 pools collateral asset / debt asset, deepest first by the debt token they hold (at most 2).
    Looked up through the factory and cached for a day."""
    key = coll_asset + ':' + debt_asset
    hit = s['pools'].get(key)
    if hit and hit['ts'] > time.time() - 86400:
        return hit['pools']
    res = aggregate([(V3_FACTORY, SEL_GET_POOL + aword(coll_asset) + aword(debt_asset) + word(f)) for f in FEES])
    found = [addr_of(r) for ok, r in res if ok and len(r) >= 66 and int(r, 16)]
    ranked = []
    if found:
        bals = aggregate([(debt_asset, SEL_BALANCE_OF + aword(p)) for p in found])
        ranked = sorted(((int(r, 16) if ok and len(r) > 2 else 0, p) for p, (ok, r) in zip(found, bals)), reverse=True)
    pools = [p for b, p in ranked if b > 0][:2]
    s['pools'][key] = {'ts': time.time(), 'pools': pools}
    return pools


def collaterals_of(account):
    h = call(EVC, SEL_GET_COLLATERALS + aword(account))
    n = at(h, 1)
    if n > 20:
        raise RuntimeError(f'bad collateral count {n}')
    return [addr_of(h[2 + (2 + i) * 64:2 + (3 + i) * 64]) for i in range(n)]


def winner_block(vault, violator, send_block, our_hash):
    """Block of the Liquidate log that took this account near our send (ours if we won)."""
    head = int(rpc('eth_blockNumber', []), 16)
    logs = rpc('eth_getLogs', [{'address': vault, 'fromBlock': hex(max(0, send_block - 300)), 'toBlock': hex(head),
                                'topics': [LIQ_TOPIC, None, '0x' + aword(violator)]}])
    ours = [int(x['blockNumber'], 16) for x in logs if x['transactionHash'].lower() == our_hash.lower()]
    if ours:
        return min(ours), None, None
    if not logs:
        return None, None, None
    first = min(logs, key=lambda x: int(x['blockNumber'], 16))
    return int(first['blockNumber'], 16), first['transactionHash'], int(first.get('transactionIndex', '0x0'), 16)


def send_live(vault, violator, coll_vault, data, gas_limit, gas_price, gross_usd, gas_cap_usd):
    import farmbot_signer
    # BSC has no base fee: the gas price is the whole bid, used as both maxFeePerGas and maxPriorityFeePerGas.
    reply = farmbot_signer.send(CHAIN, EXEC, data, 0, gas_limit, gas_price, max_priority_fee_per_gas=gas_price)
    h = None
    if isinstance(reply, dict):
        h = reply.get('txHash') or reply.get('tx_hash') or reply.get('hash')
    if not h:
        log('signer_reject', vault=vault, violator=violator, collateral=coll_vault, reply=reply)  # final, never retried
        return
    log('send', hash=h, vault=vault, violator=violator, collateral=coll_vault, gas_limit=gas_limit, max_fee=gas_price,
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
        log('send_result', hash=h, vault=vault, violator=violator, result='unknown', gas_used=None, winner_block=None)
        return
    b = int(receipt['blockNumber'], 16)
    status = int(receipt['status'], 16)
    used = int(receipt['gasUsed'], 16)
    cost = used * int(receipt.get('effectiveGasPrice', hex(gas_price)), 16)
    try:
        wb, wtx, widx = winner_block(vault, violator, b, h)
    except Exception:
        wb, wtx, widx = None, None, None
    log('send_result', hash=h, vault=vault, violator=violator, collateral=coll_vault, result='won' if status else 'lost',
        gas_used=used, gas_cost_wei=cost, send_block=b, winner_block=wb, winner_tx=wtx, winner_tx_index=widx,
        blocks_after_winner=(b - wb if wb is not None else None), gross_usd=gross_usd)


def attempt(s, vault, violator, health, liability, trigger):
    now = time.time()
    key = vault + ':' + violator
    if s['cooldown'].get(key, 0) > now:
        return
    s['cooldown'][key] = now + 120   # an unwind comes in tranches: look again after two minutes
    debt_asset = asset_of(s, vault)
    out_pools = OUT_POOLS.get(debt_asset)
    if out_pools is None:
        return
    ctx = exec_ctx()
    routes = []
    for cv in collaterals_of(violator):
        coll_asset = asset_of(s, cv)
        if coll_asset == debt_asset:
            continue
        pools = pools_for(s, coll_asset, debt_asset)
        if not pools:
            continue
        try:
            h = call(vault, SEL_CHECK_LIQUIDATION + aword(ctx[1]) + aword(violator) + aword(cv))
        except ReadBudgetExceeded:
            raise
        except Exception as e:
            if '9b314d55' not in str(e):   # 0x9b314d55: a collateral the account enabled but this vault does not accept
                log('simulate_revert', vault=vault, violator=violator, collateral=cv, error='checkLiquidation: ' + str(e)[:140])
            continue
        max_repay, max_yield = at(h, 0), at(h, 1)
        if max_repay > 0 and max_yield > 0:
            routes += [(cv, pool, max_repay, max_yield) for pool in pools]
    if not routes:
        log('opportunity_skip', vault=vault, violator=violator, health=health, reason='no_pool_for_collateral_or_nothing_to_seize',
            trigger=trigger)
        return
    bnb_usd = native_price_usd()
    if bnb_usd <= 0:
        return
    best = None
    reverts = 0
    for cv, pool, max_repay, max_yield in routes[:4]:
        top = min(max_repay, MAX_REPAY)
        prev = None
        for share in REPAY_SHARES:
            repay = int(top * share)
            if repay < MIN_REPAY:
                break
            try:
                gain = sim(calldata(vault, cv, violator, repay, pool, out_pools, 0), ctx)
            except ReadBudgetExceeded:
                raise
            except Exception as e:
                reverts += 1
                last_error = str(e)[:160]
                continue      # too large for the pool at this size: try the next smaller one
            if best is None or gain > best[0]:
                best = (gain, cv, pool, repay)
            if prev is not None and gain <= prev:
                break    # past the peak: the gain now falls with the size
            prev = gain
    if best is None:
        log('simulate_revert', vault=vault, violator=violator, health=health, routes=len(routes), sizes_reverted=reverts,
            error=last_error if reverts else 'all sizes under MIN_REPAY', trigger=trigger)
        return
    gain, cv, pool, repay = best
    gross_usd = gain / 1e18   # the gain is always USDC (18 decimals on BSC)
    try:
        gas_limit = estimate(calldata(vault, cv, violator, repay, pool, out_pools, 0), ctx) * 5 // 4
        base_price = int(rpc('eth_gasPrice', []), 16)
    except ReadBudgetExceeded:
        raise
    except Exception as e:
        log('simulate_revert', vault=vault, violator=violator, collateral=cv, health=health, error='estimate: ' + str(e)[:140])
        return
    # Price ceiling so that gasPrice x gasLimit < MAX_TX_USD (and never above MAX_FEE_WEI).
    fee_ceiling = min(MAX_FEE_WEI, int(MAX_TX_USD / bnb_usd * 1e18 / gas_limit) - 1)
    bid = int(gross_usd * BID_SHARE / bnb_usd * 1e18 / gas_limit)       # bid <= BID_SHARE of gross
    if base_price > bid:
        log('opportunity_skip', vault=vault, violator=violator, collateral=cv, health=health, gross_usd=gross_usd,
            minimum_gas_price=base_price, max_bid=bid, reason='minimum_gas_price_exceeds_bid_share', trigger=trigger)
        return
    gas_price = min(fee_ceiling, bid)
    gas_cap_usd = gas_limit * gas_price / 1e18 * bnb_usd
    if gas_price < base_price or gas_cap_usd >= MAX_TX_USD or gross_usd <= gas_cap_usd:
        log('opportunity_skip', vault=vault, violator=violator, collateral=cv, health=health, gross_usd=gross_usd,
            gas_cap_usd=gas_cap_usd, reason='gross_not_above_gas_cap', trigger=trigger)
        return
    # On-chain floor: the executor reverts unless the USDC gain covers the signed gas cap.
    min_profit = int(gas_cap_usd * 1e18) + 1
    data = calldata(vault, cv, violator, repay, pool, out_pools, min_profit)
    try:
        gain = sim(data, ctx)  # the exact bytes that would be sent
    except ReadBudgetExceeded:
        raise
    except Exception as e:
        log('simulate_revert', vault=vault, violator=violator, collateral=cv, health=health, error='final: ' + str(e)[:140])
        return
    log('opportunity', vault=vault, violator=violator, collateral=cv, pool=pool, health=health, liability_usd=liability / 1e18,
        repay=repay, gross_usd=gross_usd, gas_cap_usd=gas_cap_usd, gas_limit=gas_limit, max_fee=gas_price, priority=gas_price,
        min_profit=min_profit, simulated_gain=gain, trigger=trigger, mode=MODE)
    if MODE == 'live':
        send_live(vault, violator, cv, data, gas_limit, gas_price, gross_usd, gas_cap_usd)
    else:
        log('paper_sim', vault=vault, violator=violator, collateral=cv, result='success', gain=gain, gross_usd=gross_usd)


def scan_positions(s, positions, label):
    """accountLiquidity(account, liquidation=true) -> (collateralValue, liabilityValue) in USD 1e18 per position."""
    eligible, near = [], []
    for off in range(0, len(positions), 150):
        batch = positions[off:off + 150]
        try:
            data = aggregate([(v, SEL_ACCOUNT_LIQUIDITY + aword(a) + word(1)) for v, a in batch])
        except ReadBudgetExceeded:
            raise
        except Exception as e:
            log('scan_error', label=label, offset=off, error=str(e)[:200])
            continue
        for (v, a), (ok, ret) in zip(batch, data):
            if not ok or len(ret) < 2 + 128:
                continue      # no debt on this vault any more (accountLiquidity reverts without a controller)
            coll_value, liability = at(ret, 0), at(ret, 1)
            if liability < MIN_LIABILITY:
                continue
            health = coll_value / liability
            near.append((health, v, a))
            if coll_value < liability:
                eligible.append((liability, health, v, a))
    if label == 'full':
        near.sort(key=lambda z: abs(z[0] - 1))
        s['near'] = [[v, a] for _, v, a in near[:NEAR_COUNT]]
    log('scan', label=label, checked=len(positions), debtors=len(near), underwater=len(eligible), near=len(s['near']),
        min_health=(round(min(z[0] for z in near), 5) if near else None))
    eligible.sort(reverse=True)  # largest debt first
    for liability, health, v, a in eligible[:3]:
        try:
            attempt(s, v, a, health, liability, label)
        except ReadBudgetExceeded:
            raise
        except Exception as e:
            log('attempt_error', vault=v, violator=a, error=str(e)[:200])


def add_logs(s, logs, known):
    fresh = []
    for lg in logs:
        t = lg.get('topics', [])
        if len(t) > 1:
            p = (lg['address'].lower(), addr_of(t[1]))
            if p not in known:
                known.add(p)
                fresh.append(list(p))
    s['positions'] += fresh
    return fresh


def discover(s):
    head = int(rpc('eth_blockNumber', []), 16) - 5   # the log provider can be a few blocks behind the head
    start = s['cursor_block'] + 1 if s['cursor_block'] is not None else head - 4000
    start = max(start, head - 4000)   # at most ~30 min of 0.45 s blocks per request (bsc ranges <= 5000)
    if start > head:
        return
    logs = rpc('eth_getLogs', [{'address': list(DEBT_VAULTS), 'fromBlock': hex(start), 'toBlock': hex(head),
                                'topics': [BORROW_TOPIC]}])
    known = {(v, a) for v, a in s['positions']}
    fresh = add_logs(s, logs, known)
    s['near'] = (s['near'] + fresh)[:NEAR_COUNT + 100]   # new borrowers are watched until the next full scan
    s['cursor_block'] = head
    log('discover', from_block=start, to_block=head, logs=len(logs), added=len(fresh), universe=len(s['positions']))
    try:
        backfill(s, head, known)
    except ReadBudgetExceeded:
        raise
    except Exception as e:   # older logs unavailable right now: keep going, the same page is retried next round
        log('backfill_error', next_hi=s.get('backfill_hi'), error=str(e)[:200])


def backfill(s, head, known):
    """One-time walk backwards over older Borrow logs (the seed file covers only the newest days):
    BACKFILL_PAGES pages of 5,000 blocks per discover round until BACKFILL_DAYS before the first head."""
    if s.get('backfill_hi') is None:
        s['backfill_hi'] = min(SEED_FROM_BLOCK or head, head) - 1
        s['backfill_stop'] = head - BACKFILL_DAYS * BLOCKS_PER_DAY
    added = pages = 0
    while pages < BACKFILL_PAGES and s['backfill_hi'] > s['backfill_stop']:
        lo = max(s['backfill_hi'] - 4999, s['backfill_stop'])
        logs = rpc('eth_getLogs', [{'address': list(DEBT_VAULTS), 'fromBlock': hex(lo), 'toBlock': hex(s['backfill_hi']),
                                    'topics': [BORROW_TOPIC]}])
        added += len(add_logs(s, logs, known))
        s['backfill_hi'] = lo - 1
        pages += 1
    if pages:
        log('backfill', pages=pages, added=added, next_hi=s['backfill_hi'], stop=s['backfill_stop'],
            done=s['backfill_hi'] <= s['backfill_stop'], universe=len(s['positions']))


def feed_wait(cursor):
    q = {'address': FEED_VAULT, 'topic0': LIQ_TOPIC, 'timeout': '55'}
    if cursor:
        q['after'] = cursor
    with urllib.request.urlopen(FEED + '?' + urllib.parse.urlencode(q), timeout=65) as r:
        return json.load(r)


def main():
    s = load_state()
    s.setdefault('pools', {})
    known = {(v, a) for v, a in s['positions']}
    extra = [p for p in SEED if (p[0], p[1]) not in known]
    if extra:   # a newer seed file adds to a saved universe and forces a full scan
        s['positions'] += extra
        s['last_scan'] = 0
    if SEED_FROM_BLOCK and s.get('backfill_hi') and SEED_FROM_BLOCK <= s['backfill_hi']:
        s['backfill_hi'] = SEED_FROM_BLOCK - 1   # the seed already covers these blocks
    log('start', mode=MODE, executor=(EXEC if MODE == 'live' else PAPER_EXEC), universe=len(s['positions']),
        debt_vaults=len(DEBT_VAULTS), feed_vault=FEED_VAULT)
    while True:
        now = time.time()
        try:
            if now - s['last_discover'] >= DISCOVER_INTERVAL:
                s['last_discover'] = now
                discover(s)
            if now - s['last_scan'] >= SCAN_INTERVAL:
                s['last_scan'] = now
                s['last_poll'] = now
                scan_positions(s, s['positions'], 'full')
            elif now - s['last_poll'] >= POLL_INTERVAL:
                s['last_poll'] = now
                scan_positions(s, s['near'], 'near')
            save_state(s)
            result = feed_wait(s.get('feed_cursor'))
            s['feed_cursor'] = result.get('cursor', s.get('feed_cursor'))
            logs = result.get('logs') or []
            if result.get('gap') or any(x.get('removed') for x in logs):
                s['last_poll'] = time.time()
                scan_positions(s, s['near'], 'gap')
            elif logs:
                log('feed', events=len(logs), blocks=[x.get('blockNumber') for x in logs][:10])
                s['last_poll'] = time.time()
                s['cooldown'] = {}    # a tranche was just taken: the same account may pay again right away
                scan_positions(s, s['near'], 'liquidation_feed')
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
