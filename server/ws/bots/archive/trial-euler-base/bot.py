#!/usr/bin/env python3
"""trial-euler-base: cheap-chain trial of Euler EVK liquidations on Base (USDC debt, WETH or cbBTC collateral).

Waits on the farm feed for AnswerUpdated of the Chainlink WETH/USD aggregator the vaults' oracle reads (a price
step is what makes a position pay), plus a ~110 s safety scan of the accounts nearest to health 1. For an
underwater account it simulates the exact executor call (Morpho flash loan -> EVC batch liquidate / repay /
redeem -> one UniV3 swap -> repay) and, in live mode, sends it when the simulated gross is above the signed gas
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
CHAIN = 'base'
FEED = 'http://127.0.0.1:8546/logs/base'

MORPHO = '0xbbbbbbbbbb9cc5e90e3b3af64bdaf62c37eeffcb'     # Morpho Blue, fee-free flash loans
MULTICALL = '0xca11bde05977b3631167028862be2a173976ca11'
EVC = '0x5301c7dd20bd945d2013b48ed0dee3a284ca8989'        # vault.EVC() of all three debt vaults (probe.json)
WETH = '0x4200000000000000000000000000000000000006'
USDC = '0x833589fcd6edb6e08f4c7c32d4f71b54bda02913'
CBBTC = '0xcbb7c0000ab88b473b1f5afd9ef808440eed33bf'
# Debt vaults (asset USDC, so the profit is USDC): eUSDC-1, eUSDC-102, eUSDC-91.
DEBT_VAULTS = ('0x0a1a3b5f2041f33522c4efc754a7d096f880ee16', '0xeef57677c2fc1a930eed234e3545e750c88f6743',
               '0x91a9ed5d4368499b1fe41f721ab13e64760b3f05')
# Collateral asset -> UniV3 0.05% pool against USDC (factory getPool, probe.py). Any collateral vault of one of
# these assets is in scope; everything else is skipped.
POOLS = {WETH: '0xd0b53d9277642d899df5c87a3966a349a798f224', CBBTC: '0xfbb6eed8e7aa03b138556eedaf5d271a5e1e43ef'}
WETH_USDC_POOL = POOLS[WETH]
AGGREGATOR = '0x05c84a58fe042275b37db038baacd15f410c7bb0'  # Chainlink WETH/USD aggregator behind feed 0x71041ddd...
ANSWER_TOPIC = '0x0559884fd3a460db3073b7fc896cc77986f16e378210ded43186175bf646fc5f'   # AnswerUpdated(int256,uint256,uint256)
BORROW_TOPIC = '0xcbc04eca7e9da35cb1393a6135a199ca52e450d5e9251cbd99f7847d33a36750'   # Borrow(address,uint256)
LIQ_TOPIC = '0x8246cc71ab01533b5bebc672a636df812f10637ad720797319d5741d5ebb3962'      # Liquidate(address,address,address,uint256,uint256)
SEL_RUN = '0x2242626e'          # run((address,address,address,address,uint256,uint256,address,uint256))
SEL_ACCOUNT_LIQUIDITY = '0xa824bf67'   # accountLiquidity(address,bool)
SEL_CHECK_LIQUIDATION = '0x88aa6f12'   # checkLiquidation(address,address,address)
SEL_GET_COLLATERALS = '0xa4d25d1e'     # getCollaterals(address)
SEL_ASSET = '0x38d52e0f'
SEL_SLOT0 = '0x3850c7bd'
SEL_TRY_AGGREGATE = '0xbce38bd7'

PAPER_EXEC = '0xfe00ddfee1423e3dba3e07a1b0f78b0ac1df8e9a'   # fork deployment; paper code override only
PAPER_OWNER = '0xc0ffee0000000000000000000000000000000002'  # the owner baked into that runtime
EXEC = os.environ.get('EXECUTOR_ADDR_BASE') or os.environ.get('EXECUTOR_ADDR')
if MODE == 'live' and not EXEC:
    raise SystemExit('EXECUTOR_ADDR_BASE or EXECUTOR_ADDR is required in live mode')
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
BACKFILL_DAYS = 45
BACKFILL_PAGES = 6        # per discover round: 6 x 60 CU every 10 min until done (~390 pages, ~23,400 CU once)

# ---- loss guard -----------------------------------------------------------------------------
MAX_TX_USD = 0.90          # signed gas cap (maxFeePerGas x gasLimit + L1 fee allowance) stays under this
L1_FEE_ALLOWANCE_USD = 0.02  # Base L1 data fee for ~300 bytes of calldata, generous
MAX_FEE_WEI = 500_000_000  # 0.5 gwei absolute ceiling for maxFeePerGas
BID_SHARE = 0.50           # priority fee bid: at most this share of the simulated gross
MAX_REPAY = 50_000_000_000  # 50,000 USDC per call, flash-loaned, never the bot's own funds
SWEEP_MIN = 2_000_000_000   # repayments of 2,000 USDC or more also try smaller sizes (pool slippage)
REPAY_SHARES = (1.0, 0.5, 0.25, 0.12)
MIN_LIABILITY = 5 * 10**18  # skip accounts with less than 5 USD of debt (unit of account USD, 18 decimals)
RELAY_CU_CAP = 75_000      # per UTC day; the feed's own CU is metered separately

NEAR_COUNT = 150
SCAN_INTERVAL = 3600
POLL_INTERVAL = 100        # with the 55 s feed timeout the safety cadence is ~110 s; price events scan at once
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
    return {'positions': SEED, 'near': [], 'cursor_block': None, 'feed_cursor': None, 'assets': {},
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


def eth_price_usd():
    """USDC per WETH from the UniV3 WETH/USDC 0.05% pool (token0 = WETH 18 dec, token1 = USDC 6 dec)."""
    sqrt_p = at(call(WETH_USDC_POOL, SEL_SLOT0), 0)
    return (sqrt_p / 2**96) ** 2 * 1e12


def calldata(vault, coll_vault, violator, repay, pool, min_profit):
    # Params is a static tuple: eight words after the selector.
    return (SEL_RUN + aword(MORPHO) + aword(vault) + aword(coll_vault) + aword(violator) + word(repay) + word(0)
            + aword(pool) + word(min_profit))


def exec_ctx():
    if MODE == 'live':
        return bot_address(), EXEC, None
    return PAPER_OWNER, PAPER_EXEC, {PAPER_EXEC: {'code': RUNTIME}}


def sim(data, ctx):
    frm, to, ov = ctx
    params = [{'from': frm, 'to': to, 'data': data, 'gas': hex(2_500_000)}, 'latest'] + ([ov] if ov else [])
    return at(rpc('eth_call', params), 0)


def estimate(data, ctx):
    frm, to, ov = ctx
    params = [{'from': frm, 'to': to, 'data': data}, 'latest'] + ([ov] if ov else [])
    return int(rpc('eth_estimateGas', params), 16)


def asset_of(s, vault):
    if vault not in s['assets']:
        s['assets'][vault] = addr_of(call(vault, SEL_ASSET))
    return s['assets'][vault]


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


def send_live(vault, violator, coll_vault, data, gas_limit, max_fee, priority, gross_usd, gas_cap_usd):
    import farmbot_signer
    reply = farmbot_signer.send(CHAIN, EXEC, data, 0, gas_limit, max_fee, max_priority_fee_per_gas=priority)
    h = None
    if isinstance(reply, dict):
        h = reply.get('txHash') or reply.get('tx_hash') or reply.get('hash')
    if not h:
        log('signer_reject', vault=vault, violator=violator, collateral=coll_vault, reply=reply)  # final, never retried
        return
    log('send', hash=h, vault=vault, violator=violator, collateral=coll_vault, gas_limit=gas_limit, max_fee=max_fee,
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
        log('send_result', hash=h, vault=vault, violator=violator, result='unknown', gas_used=None, winner_block=None)
        return
    b = int(receipt['blockNumber'], 16)
    status = int(receipt['status'], 16)
    used = int(receipt['gasUsed'], 16)
    cost = used * int(receipt['effectiveGasPrice'], 16) + int(receipt.get('l1Fee', '0x0'), 16)
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
    s['cooldown'][key] = now + 300
    ctx = exec_ctx()
    routes = []
    for cv in collaterals_of(violator):
        pool = POOLS.get(asset_of(s, cv))
        if not pool:
            continue
        try:
            h = call(vault, SEL_CHECK_LIQUIDATION + aword(ctx[1]) + aword(violator) + aword(cv))
        except ReadBudgetExceeded:
            raise
        except Exception as e:
            log('simulate_revert', vault=vault, violator=violator, collateral=cv, error='checkLiquidation: ' + str(e)[:140])
            continue
        max_repay, max_yield = at(h, 0), at(h, 1)
        if max_repay > 0 and max_yield > 0:
            routes.append((cv, pool, max_repay, max_yield))
    if not routes:
        log('opportunity_skip', vault=vault, violator=violator, health=health, reason='no_supported_collateral_or_nothing_to_seize',
            trigger=trigger)
        return
    eth_usd = eth_price_usd()
    if eth_usd <= 0:
        return
    best = None
    for cv, pool, max_repay, max_yield in routes:
        top = min(max_repay, MAX_REPAY)
        shares = REPAY_SHARES if top >= SWEEP_MIN else REPAY_SHARES[:1]
        prev = None
        for share in shares:
            repay = int(top * share)
            if repay <= 0:
                continue
            try:
                gain = sim(calldata(vault, cv, violator, repay, pool, 0), ctx)
            except ReadBudgetExceeded:
                raise
            except Exception as e:
                log('simulate_revert', vault=vault, violator=violator, collateral=cv, repay=repay, health=health,
                    max_repay=max_repay, max_yield=max_yield, error=str(e)[:160])
                continue
            if best is None or gain > best[0]:
                best = (gain, cv, pool, repay)
            if prev is not None and gain <= prev:
                break    # past the peak: the gain now falls with the size
            prev = gain
    if best is None:
        return
    gain, cv, pool, repay = best
    gross_usd = gain / 1e6
    try:
        gas_limit = estimate(calldata(vault, cv, violator, repay, pool, 0), ctx) * 5 // 4
        base_price = int(rpc('eth_gasPrice', []), 16)
    except ReadBudgetExceeded:
        raise
    except Exception as e:
        log('simulate_revert', vault=vault, violator=violator, collateral=cv, health=health, error='estimate: ' + str(e)[:140])
        return
    # Fee ceiling so that maxFeePerGas x gasLimit + L1 allowance < MAX_TX_USD (and never above 0.5 gwei).
    fee_ceiling = min(MAX_FEE_WEI, int((MAX_TX_USD - L1_FEE_ALLOWANCE_USD) / eth_usd * 1e18 / gas_limit))
    priority = int(gross_usd * BID_SHARE / eth_usd * 1e18 / gas_limit)       # bid <= BID_SHARE of gross
    priority = max(0, min(priority, fee_ceiling - 2 * base_price))
    max_fee = min(fee_ceiling, 2 * base_price + priority)
    gas_cap_usd = gas_limit * max_fee / 1e18 * eth_usd + L1_FEE_ALLOWANCE_USD
    if max_fee < base_price + priority or gas_cap_usd >= MAX_TX_USD or gross_usd <= gas_cap_usd:
        log('opportunity_skip', vault=vault, violator=violator, collateral=cv, health=health, gross_usd=gross_usd,
            gas_cap_usd=gas_cap_usd, reason='gross_not_above_gas_cap', trigger=trigger)
        return
    # On-chain floor: the executor reverts unless the USDC gain covers the signed gas cap.
    min_profit = int(gas_cap_usd * 1e6) + 1
    data = calldata(vault, cv, violator, repay, pool, min_profit)
    try:
        gain = sim(data, ctx)  # the exact bytes that would be sent
    except ReadBudgetExceeded:
        raise
    except Exception as e:
        log('simulate_revert', vault=vault, violator=violator, collateral=cv, health=health, error='final: ' + str(e)[:140])
        return
    log('opportunity', vault=vault, violator=violator, collateral=cv, pool=pool, health=health, liability_usd=liability / 1e18,
        repay=repay, gross_usd=gross_usd, gas_cap_usd=gas_cap_usd, gas_limit=gas_limit, max_fee=max_fee, priority=priority,
        min_profit=min_profit, simulated_gain=gain, trigger=trigger, mode=MODE)
    if MODE == 'live':
        send_live(vault, violator, cv, data, gas_limit, max_fee, priority, gross_usd, gas_cap_usd)
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


def discover(s):
    head = int(rpc('eth_blockNumber', []), 16)
    start = s['cursor_block'] + 1 if s['cursor_block'] is not None else head - 3000
    start = max(start, head - 9000)   # at most ~30 min of 0.2 s blocks per request
    if start > head:
        return
    logs = rpc('eth_getLogs', [{'address': list(DEBT_VAULTS), 'fromBlock': hex(start), 'toBlock': hex(head),
                                'topics': [BORROW_TOPIC]}])
    known = {(v, a) for v, a in s['positions']}
    fresh = []
    for lg in logs:
        t = lg.get('topics', [])
        if len(t) > 1:
            p = (lg['address'].lower(), addr_of(t[1]))
            if p not in known:
                known.add(p)
                fresh.append(list(p))
    s['positions'] += fresh
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
    """One-time walk backwards over older Borrow logs (the seed file covers only what the public node served):
    BACKFILL_PAGES pages of 49,999 blocks per discover round until BACKFILL_DAYS before the first head."""
    if s.get('backfill_hi') is None:
        s['backfill_hi'] = min(SEED_FROM_BLOCK or head, head) - 1
        s['backfill_stop'] = head - BACKFILL_DAYS * 432000
    added = pages = 0
    while pages < BACKFILL_PAGES and s['backfill_hi'] > s['backfill_stop']:
        lo = max(s['backfill_hi'] - 49999, s['backfill_stop'])
        logs = rpc('eth_getLogs', [{'address': list(DEBT_VAULTS), 'fromBlock': hex(lo), 'toBlock': hex(s['backfill_hi']),
                                    'topics': [BORROW_TOPIC]}])
        for lg in logs:
            t = lg.get('topics', [])
            if len(t) > 1:
                p = (lg['address'].lower(), addr_of(t[1]))
                if p not in known:
                    known.add(p)
                    s['positions'].append(list(p))
                    added += 1
        s['backfill_hi'] = lo - 1
        pages += 1
    if pages:
        log('backfill', pages=pages, added=added, next_hi=s['backfill_hi'], stop=s['backfill_stop'],
            done=s['backfill_hi'] <= s['backfill_stop'], universe=len(s['positions']))


def feed_wait(cursor):
    q = {'address': AGGREGATOR, 'topic0': ANSWER_TOPIC, 'timeout': '55'}
    if cursor:
        q['after'] = cursor
    with urllib.request.urlopen(FEED + '?' + urllib.parse.urlencode(q), timeout=65) as r:
        return json.load(r)


def main():
    s = load_state()
    log('start', mode=MODE, executor=(EXEC if MODE == 'live' else PAPER_EXEC), universe=len(s['positions']),
        debt_vaults=DEBT_VAULTS, pools=POOLS)
    while True:
        now = time.time()
        try:
            if now - s['last_discover'] >= DISCOVER_INTERVAL:
                s['last_discover'] = now
                discover(s)
            if now - s['last_scan'] >= SCAN_INTERVAL:
                s['last_scan'] = now
                scan_positions(s, s['positions'], 'full')
            elif now - s['last_poll'] >= POLL_INTERVAL:
                s['last_poll'] = now
                scan_positions(s, s['near'], 'near')
            save_state(s)
            result = feed_wait(s.get('feed_cursor'))
            s['feed_cursor'] = result.get('cursor', s.get('feed_cursor'))
            logs = result.get('logs') or []
            if result.get('gap') or any(x.get('removed') for x in logs):
                scan_positions(s, s['near'], 'gap')
            elif logs:
                log('feed', events=len(logs), blocks=[x.get('blockNumber') for x in logs][:10])
                s['last_poll'] = time.time()
                scan_positions(s, s['near'], 'price_feed')
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
            log('feed_error', error=str(e)[:180])   # 429/503/timeout: fall back to a state re-read
            try:
                scan_positions(s, s['near'], 'gap')
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
