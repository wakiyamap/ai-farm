#!/usr/bin/env python3
"""trial-felix-liq-hyperevm: cheap-chain trial of Felix (Liquity V2 fork, HyperEVM) trove liquidations.

TroveManager.batchLiquidateTroves(ids) is public and pays the caller 0.5 % of each liquidated trove's
collateral; the debt is absorbed by the Stability Pool, so the caller needs no principal. One Multicall3
eth_call per poll reads every branch's price (PriceFeed.fetchPrice) and every trove's debt and collateral
(getLatestTroveData); ICR = coll x price / debt is computed here. When a trove is under the branch MCR the bot
simulates the exact executor call and, in live mode, sends it when the simulated reward is above the signed gas
cap. The poll runs on a timer that shortens as the riskiest trove nears MCR. A lost attempt costs gas only.

`python3 bot.py selftest <block>` runs one detection + simulation at a past block and prints the result.
"""
import sys
sys.path.append("/opt/farm/lib")  # live service does not put the signer library on the path
import datetime
import json
import os
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
MODE = os.environ.get('BOT_MODE', 'paper')
LANE = os.environ.get('RPC_LANE', 'paper')
RELAY = os.environ['RPC_RELAY_URL'].rstrip('/')
CHAIN = 'hyperevm'

MULTICALL = '0xca11bde05977b3631167028862be2a173976ca11'
WHYPE = '0x5555555555555555555555555555555555555555'
KHYPE = '0xfd739d4e423301ce9385c1fb8850539d657c296d'
ZERO = '0x' + '00' * 20
# Felix branches (docs usefelix.gitbook.io market-1-feusd-cdp; TroveManager getters read on chain 2026-11-18).
# pool = UniV3-style {collateral, WHYPE} pool the executor sells the reward on; none needed for WHYPE.
# The UBTC branch (0xbbe5f227...) is not covered: no route to native is fork-proven for it.
BRANCHES = [
    {'name': 'WHYPE', 'tm': '0x3100f4e7bda2ed2452d9a57eb30260ab071bbe62', 'coll': WHYPE, 'pool': ZERO},
    {'name': 'kHYPE', 'tm': '0x7c07bb77b1cf9a5b40d92f805c10d90c90957e4a', 'coll': KHYPE,
     'pool': '0xbe352daf66af94ccf2012a154a67daef95facb91'},
]
SEL_COUNT = '0x4aff96e1'      # getTroveIdsCount()
SEL_ID_AT = '0x1ef11b62'      # getTroveFromTroveIdsArray(uint256)
SEL_TROVE = '0xaad3f404'      # getLatestTroveData(uint256) -> (entireDebt, entireColl, ...)
SEL_PRICE = '0x0fdb11cf'      # fetchPrice() -> (price 1e18, bool)
SEL_MCR = '0x794e5724'        # MCR() on BorrowerOperations
SEL_BO = '0x77553ad4'         # borrowerOperations() on the TroveManager
SEL_TAKE = '0xba55d33a'       # take(address,uint256[],address,address,address,uint256), cast sig
SEL_TRY = '0xbce38bd7'        # Multicall3 tryAggregate(bool,(address,bytes)[])
T_LIQ = '0x7243af9a1cff94d3429b2ee00b78c1c10589259f20dc167cb67704f38f9e824e'  # Liquidation(uint256 x10), cast keccak
NOTHING = '8c20998d'          # NothingToLiquidate()

PAPER_EXEC = '0x7986a41cf80d6d20f7b96c11f600b7882ab29e2c'   # fork deployment; paper code override only
PAPER_OWNER = '0xc0ffee0000000000000000000000000000002378'  # the owner baked into that fork deployment
EXEC = os.environ.get('EXECUTOR_ADDR_HYPEREVM') or os.environ.get('EXECUTOR_ADDR')
if MODE == 'live' and not EXEC:
    raise SystemExit('EXECUTOR_ADDR_HYPEREVM or EXECUTOR_ADDR is required in live mode')
RUNTIME = (HERE / 'executor-runtime.hex').read_text().strip()
if not RUNTIME.startswith('0x') or len(RUNTIME) < 100:
    raise SystemExit('missing paper executor runtime')

LOG = HERE / 'logs' / 'bot.jsonl'
STATE = HERE / 'state' / 'state.json'
CU_FILE = HERE / 'state' / 'cu.json'

# ---- loss guard -----------------------------------------------------------------------------
MAX_TX_USD = 0.90          # signed gas cap (maxFeePerGas x gasLimit) stays under this
MAX_FEE_WEI = 100 * 10**9  # absolute ceiling for maxFeePerGas (the USD cap binds first; base fee ~0.1 gwei)
MAX_GAS = 1_900_000        # HyperEVM: every transaction must fit in 2,000,000 gas
BID_SHARE = 0.50           # priority fee bid: at most this share of the simulated gross
MAX_IDS = 2                # troves per transaction, largest collateral first (measured gas limit with the
                           # 1.25 margin: 821k for one trove, 1.08M for two; HyperEVM allows 2M)
MAX_SENDS_DAY = 15         # live sends per UTC day
RELAY_CU_CAP = 90_000      # per UTC day
LIST_INTERVAL = 1800       # trove id list refresh
COOLDOWN = 45              # seconds before the same trove is tried again
CU_COST = {'eth_call': 26, 'eth_estimateGas': 20, 'eth_getLogs': 60, 'eth_getTransactionReceipt': 20,
           'eth_blockNumber': 10, 'eth_gasPrice': 20, 'eth_getStorageAt': 20}
_id = 0


class ReadBudgetExceeded(Exception):
    pass


def log(ev, **kw):
    row = {'ts': round(time.time(), 3), 'ev': ev, **kw}
    if SELFTEST:
        print(json.dumps(row, default=str), flush=True)
        return
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
    if not SELFTEST:
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


def multicall(calls, block='latest'):
    """Multicall3 tryAggregate(false, [(target, data)]). Returns [(ok, hex data without 0x)]."""
    starts, acc = [], 32 * len(calls)
    for _, data in calls:
        starts.append(acc)
        size = (len(data) - 2) // 2
        acc += 96 + ((size + 31) // 32) * 32
    enc = SEL_TRY + word(0) + word(64) + word(len(calls)) + ''.join(word(x) for x in starts)
    for target, data in calls:
        size = (len(data) - 2) // 2
        enc += aword(target) + word(64) + word(size) + data[2:].ljust(((size + 31) // 32) * 64, '0')
    h = rpc('eth_call', [{'to': MULTICALL, 'data': enc}, block])[2:]
    if len(h) < 128:
        raise RuntimeError('short Multicall answer')
    n = int(h[64:128], 16)
    if n != len(calls):
        raise RuntimeError(f'Multicall returned {n} of {len(calls)}')
    out = []
    for i in range(n):
        start = 128 + int(h[128 + i * 64:192 + i * 64], 16) * 2
        ok = int(h[start:start + 64], 16) != 0
        off = int(h[start + 64:start + 128], 16)
        length = int(h[start + off * 2:start + off * 2 + 64], 16)
        out.append((ok, h[start + off * 2 + 64:start + off * 2 + 64 + length * 2]))
    return out


def setup(block='latest'):
    """Per branch: price feed (TroveManager storage slot 2, LiquityBaseInit.PRICE_FEED_SLOT) and MCR."""
    for b in BRANCHES:
        b['feed'] = '0x' + rpc('eth_getStorageAt', [b['tm'], '0x2', block])[-40:]
        bo = '0x' + rpc('eth_call', [{'to': b['tm'], 'data': SEL_BO}, block])[-40:]
        b['mcr'] = int(rpc('eth_call', [{'to': bo, 'data': SEL_MCR}, block]), 16)
        if int(b['feed'], 16) == 0 or not 10**18 < b['mcr'] < 3 * 10**18:
            raise SystemExit(f'bad branch setup {b}')


def load_ids(block='latest'):
    counts = multicall([(b['tm'], SEL_COUNT) for b in BRANCHES], block)
    calls, owner = [], []
    for b, (ok, data) in zip(BRANCHES, counts):
        n = int(data, 16) if ok and data else 0
        if n > 400:
            raise RuntimeError(f'{b["name"]}: {n} troves, more than this bot reads in one call')
        for i in range(n):
            calls.append((b['tm'], SEL_ID_AT + word(i)))
            owner.append(b['name'])
    ids = {b['name']: [] for b in BRANCHES}
    if calls:
        for name, (ok, data) in zip(owner, multicall(calls, block)):
            if ok and data:
                ids[name].append(int(data, 16))
    return ids


def read_all(ids, block='latest'):
    """One eth_call: every branch price and every trove's (debt, coll). Returns {name: (price, [(icr, coll, debt, id)])}."""
    calls = [(b['feed'], SEL_PRICE) for b in BRANCHES]
    index = []
    for b in BRANCHES:
        for t in ids[b['name']]:
            calls.append((b['tm'], SEL_TROVE + word(t)))
            index.append((b['name'], t))
    res = multicall(calls, block)
    prices = {}
    for b, (ok, data) in zip(BRANCHES, res):
        if not ok or len(data) < 64:
            raise RuntimeError(f'{b["name"]}: fetchPrice failed')
        prices[b['name']] = int(data[:64], 16)
    out = {b['name']: (prices[b['name']], []) for b in BRANCHES}
    for (name, t), (ok, data) in zip(index, res[len(BRANCHES):]):
        if not ok or len(data) < 128:
            continue
        debt, coll = int(data[:64], 16), int(data[64:128], 16)
        if debt == 0 or coll == 0:
            continue          # closed trove
        out[name][1].append((coll * prices[name] // debt, coll, debt, t))
    return out


def take_data(b, trove_ids, min_profit):
    """ABI encoding of take(troveManager, troveIds[], collateral, wnative, pool, minProfit); selftest compares
    it with `cast calldata` (scratch/trial-felix-liq/sigs.py prints the reference)."""
    return (SEL_TAKE + aword(b['tm']) + word(192) + aword(b['coll']) + aword(WHYPE) + aword(b['pool']) + word(min_profit)
            + word(len(trove_ids)) + ''.join(word(t) for t in trove_ids))


def bot_address():
    import farmbot_signer
    a = farmbot_signer.my_address()
    a = a.get('address') if isinstance(a, dict) else a   # my_address() returns {"ok":..., "address":...}
    if not isinstance(a, str) or len(a) != 42:
        raise RuntimeError('signer my_address returned no address')
    return a


def exec_ctx():
    if MODE == 'live':
        return bot_address(), EXEC, None
    return PAPER_OWNER, PAPER_EXEC, {PAPER_EXEC: {'code': RUNTIME}}


def sim(data, ctx, block='latest'):
    frm, to, ov = ctx
    params = [{'from': frm, 'to': to, 'data': data, 'gas': hex(MAX_GAS)}, block] + ([ov] if ov else [])
    return int(rpc('eth_call', params)[2:66], 16)


def estimate(data, ctx, block='latest'):
    frm, to, ov = ctx
    params = [{'from': frm, 'to': to, 'data': data}, block] + ([ov] if ov else [])
    return int(rpc('eth_estimateGas', params), 16)


def winner(b, send_block, our_hash):
    """Block and tx of the Liquidation on this branch near our send (ours if we won)."""
    head = int(rpc('eth_blockNumber', []), 16)
    logs = rpc('eth_getLogs', [{'address': b['tm'], 'fromBlock': hex(max(0, send_block - 300)), 'toBlock': hex(head),
                                'topics': [T_LIQ]}])
    if not logs:
        return None, None
    for x in logs:
        if x['transactionHash'].lower() == our_hash.lower():
            return int(x['blockNumber'], 16), x['transactionHash']
    first = min(logs, key=lambda x: int(x['blockNumber'], 16))
    return int(first['blockNumber'], 16), first['transactionHash']


def send_live(s, b, trove_ids, data, gas_limit, max_fee, priority, gross_usd, gas_cap_usd):
    import farmbot_signer
    day = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    if s.get('send_day') != day:
        s['send_day'], s['sends'] = day, 0
    if s['sends'] >= MAX_SENDS_DAY:
        log('opportunity_skip', branch=b['name'], troves=[str(t) for t in trove_ids], reason='daily_send_cap')
        return
    s['sends'] += 1
    reply = farmbot_signer.send(CHAIN, EXEC, data, 0, gas_limit, max_fee, max_priority_fee_per_gas=priority)
    h = None
    if isinstance(reply, dict):
        h = reply.get('txHash') or reply.get('tx_hash') or reply.get('hash')
    if not h:
        log('signer_reject', branch=b['name'], reply=reply)  # final, never retried
        return
    log('send', hash=h, branch=b['name'], troves=[str(t) for t in trove_ids], gas_limit=gas_limit, max_fee=max_fee,
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
        log('send_result', hash=h, branch=b['name'], result='unknown', gas_used=None, winner_block=None)
        return
    blk = int(receipt['blockNumber'], 16)
    status = int(receipt['status'], 16)
    used = int(receipt['gasUsed'], 16)
    cost = used * int(receipt['effectiveGasPrice'], 16)
    try:
        wb, wtx = winner(b, blk, h)
    except Exception:
        wb, wtx = None, None
    log('send_result', hash=h, branch=b['name'], result='won' if status else 'lost', gas_used=used, gas_cost_wei=cost,
        send_block=blk, winner_block=wb, winner_tx=wtx, blocks_after_winner=(blk - wb if wb is not None else None),
        gross_usd=gross_usd)


def attempt(s, b, under, hype_usd, block='latest'):
    """under: [(icr, coll, debt, id)] of this branch with ICR < MCR."""
    now = time.time()
    cool = s.setdefault('cooldown', {})
    todo = [u for u in sorted(under, key=lambda u: -u[1]) if cool.get(str(u[3]), 0) <= now][:MAX_IDS]
    if not todo:
        return
    trove_ids = [u[3] for u in todo]
    for t in trove_ids:
        cool[str(t)] = now + COOLDOWN
    ctx = exec_ctx()
    info = dict(branch=b['name'], troves=[str(t) for t in trove_ids], icr=[round(u[0] / 1e18, 5) for u in todo],
                coll=[round(u[1] / 1e18, 6) for u in todo], mcr=b['mcr'] / 1e18)
    try:
        gain = sim(take_data(b, trove_ids, 1), ctx, block)
        gas_limit = estimate(take_data(b, trove_ids, 1), ctx, block) * 5 // 4
        base_price = int(rpc('eth_gasPrice', []), 16)
    except ReadBudgetExceeded:
        raise
    except Exception as e:
        log('simulate_revert', error=str(e)[:200], taken_or_healthy=NOTHING in str(e), **info)
        return
    gross_usd = gain / 1e18 * hype_usd
    if gas_limit > MAX_GAS:
        log('opportunity_skip', gross_usd=gross_usd, gas_limit=gas_limit, reason='over_hyperevm_gas_limit', **info)
        return
    # Fee ceiling so that maxFeePerGas x gasLimit < MAX_TX_USD (and never above MAX_FEE_WEI).
    fee_ceiling = min(MAX_FEE_WEI, int(MAX_TX_USD * 0.98 / hype_usd * 1e18 / gas_limit))
    priority = int(gain * BID_SHARE / gas_limit)                 # bid <= BID_SHARE of the simulated gross
    priority = max(0, min(priority, fee_ceiling - 2 * base_price))
    max_fee = min(fee_ceiling, 2 * base_price + priority)
    gas_cap_wei = gas_limit * max_fee
    gas_cap_usd = gas_cap_wei / 1e18 * hype_usd
    if max_fee < base_price + priority or gas_cap_usd >= MAX_TX_USD or gain <= gas_cap_wei:
        log('opportunity_skip', gross_usd=gross_usd, gas_cap_usd=gas_cap_usd, base_fee=base_price,
            reason='gross_not_above_gas_cap_or_base_fee_above_cap', **info)
        return
    # On-chain floor: the executor reverts unless its native gain covers the signed gas cap.
    min_profit = gas_cap_wei + 1
    data = take_data(b, trove_ids, min_profit)
    try:
        gain = sim(data, ctx, block)  # the exact bytes that would be sent
    except ReadBudgetExceeded:
        raise
    except Exception as e:
        log('simulate_revert', error='final: ' + str(e)[:180], **info)
        return
    log('opportunity', gross_usd=gross_usd, gain_wei=gain, gas_cap_usd=gas_cap_usd, gas_limit=gas_limit, max_fee=max_fee,
        priority=priority, min_profit=min_profit, hype_usd=hype_usd, mode=MODE, **info)
    if SELFTEST:
        return
    if MODE == 'live':
        send_live(s, b, trove_ids, data, gas_limit, max_fee, priority, gross_usd, gas_cap_usd)
    else:
        log('paper_sim', branch=b['name'], troves=[str(t) for t in trove_ids], result='success', gain_wei=gain,
            gross_usd=gross_usd)


def check(s, ids, block='latest'):
    """One poll. Returns the smallest (ICR - MCR) / MCR over all troves, as a fraction."""
    data = read_all(ids, block)
    hype_usd = data['WHYPE'][0] / 1e18
    if not 1 <= hype_usd <= 10_000:
        raise RuntimeError(f'bad HYPE price {hype_usd}')
    margin, nearest = None, None
    for b in BRANCHES:
        price, troves = data[b['name']]
        under = [u for u in troves if u[0] < b['mcr']]
        for u in troves:
            m = (u[0] - b['mcr']) / b['mcr']
            if u[0] >= b['mcr'] and (margin is None or m < margin):
                margin, nearest = m, (b['name'], str(u[3]), round(u[1] / 1e18, 4))
        if under:
            attempt(s, b, under, hype_usd, block)
    s['polls'] = s.get('polls', 0) + 1
    if SELFTEST or s['polls'] % 20 == 1:
        log('check', troves={b['name']: len(data[b['name']][1]) for b in BRANCHES},
            price={b['name']: round(data[b['name']][0] / 1e18, 4) for b in BRANCHES},
            min_margin=None if margin is None else round(margin, 5), nearest=nearest)
    return margin


def interval(margin):
    if margin is None:
        return 60
    if margin < 0.015:
        return 4
    if margin < 0.04:
        return 12
    return 60


def load_state():
    if STATE.exists():
        try:
            return json.loads(STATE.read_text())
        except Exception:
            pass
    return {'cooldown': {}}


def save_state(s):
    now = time.time()
    s['cooldown'] = {k: v for k, v in s.get('cooldown', {}).items() if v > now}
    tmp = STATE.with_suffix('.tmp')
    tmp.write_text(json.dumps(s, separators=(',', ':')))
    tmp.replace(STATE)


def main():
    LOG.parent.mkdir(exist_ok=True)
    STATE.parent.mkdir(exist_ok=True)
    s = load_state()
    setup()
    ids, last_list = load_ids(), time.time()
    log('start', mode=MODE, executor=(EXEC if MODE == 'live' else PAPER_EXEC),
        branches={b['name']: {'mcr': b['mcr'] / 1e18, 'feed': b['feed'], 'troves': len(ids[b['name']])} for b in BRANCHES})
    while True:
        wait = 60
        try:
            if time.time() - last_list >= LIST_INTERVAL:
                ids, last_list = load_ids(), time.time()
            wait = interval(check(s, ids))
        except ReadBudgetExceeded as e:
            log('read_budget', error=str(e))
            wait = 600
        except Exception as e:
            log('loop_error', error=str(e)[:250])
            wait = 30
        save_state(s)
        time.sleep(wait)


SELFTEST = len(sys.argv) > 2 and sys.argv[1] == 'selftest'
if __name__ == '__main__':
    if SELFTEST:
        blk = hex(int(sys.argv[2]))
        setup(blk)
        check({'cooldown': {}}, load_ids(blk), blk)
    else:
        main()
