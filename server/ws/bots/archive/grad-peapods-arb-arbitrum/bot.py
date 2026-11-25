"""grad-peapods-arb-arbitrum: Peapods pod bond / debond round trips on Arbitrum, one atomic executor call.

Graduated from trial-peapods-arb-arbitrum (live 2026-11-19 19:25Z: 10 sends, 5 won, +0.00263 ETH net; decision
2026-11-24-graduate-and-builder-focus.md). Same executor and the same eight routes. What changed is the time from
"a swap happened" to "our transaction is signed", because all five lost sends landed 0-3 blocks (under 1 s) after
the winner and 19 more gains were gone before the gas estimate:

  trial: probe -> block -> 4 size calls -> estimate -> guarded call -> sign     (8 relay round trips in series)
  grad:  [probe x 3 sizes + block + gas estimate per route, all at once] -> sign  (1 round trip)

and it also wakes on a Swap of the pod pairs themselves (where a gap opens), not only on the PEAS/WETH pool.
A pod round trip is flash-funded WETH; the executor reverts unless its WETH balance grew by minProfit after the
loan is repaid, so a lost attempt costs gas only. Arbitrum orders first come first served: no fee is bid.
"""
import concurrent.futures
import datetime
import json
import os
import queue
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.append('/opt/farm/lib')   # farmbot_signer lives here; the live service does not add it

HERE = Path(__file__).resolve().parent
MODE = os.environ.get('BOT_MODE', 'paper')
LANE = os.environ.get('RPC_LANE', 'paper')
RELAY = os.environ['RPC_RELAY_URL'].rstrip('/')
CHAIN = 'arbitrum'
FEED = 'http://127.0.0.1:8546/logs/arbitrum'

# Addresses: read from the incumbents' takes and checked with token0()/token1()/asset()/symbol() getters by the
# trial (scratch/flashcensus/pairinfo.py); unchanged here, and used live by the trial since 2026-11-19.
VAULT = '0xba12222222228d8ba445958a75a0704d566bf2c8'        # Balancer V2 Vault, flash loan fee 0
WETH = '0x82af49447d8a07e3bd95bd0d56f35241523fbab1'
PEAS = '0x02f92800f57bcd74066f5709f1daa1a4302df875'
ARB = '0x912ce59144191c1204e64559fe8253a0e49e6548'
USDC = '0xaf88d065e77c8cc2239327c5edb3a432268e5831'
OHM = '0xf0cb2dc0db5e6c66b9a70ac27b06b878da017028'
PEAS_WETH = '0x23d17764f41aea93fdbb5beffa83571f0bf3f8b2'    # Uniswap V3 PEAS/WETH 1 pct
ARB_WETH = '0xc6f780497a95e246eb9449f5e4770916dcd6396a'     # Uniswap V3 WETH/ARB 0.05 pct
WETH_USDC = '0xc6962004f452be9203591991d15f6b388e09e8d0'    # Uniswap V3 WETH/USDC 0.05 pct
P_PEAS = '0x4548c7fafefd9e18dbfd583f2b43b67b3b4d4c0a'       # pod pPEAS (underlying PEAS)
PF_PPEAS = '0x8605e3bf88ac794372975781fb50fcdb3fd7fe53'     # ERC4626 pfpPEAS-30 (asset pPEAS)
P_ARB = '0x1ad188574b5dd5268e71aee3cabcd3723db65c49'        # pod pARB (underlying ARB)
PAIR_PARB = '0x4834f2d4e7bc49bacfbc0df551ee57fa39443110'    # UNI-V2 pARB / pfpPEAS-30
AP_PEASUSDC = '0xc604c6c646bb7a49d5829fbc479bb7b1b4da17f3'  # pod apPEASUSDC (underlying PEAS)
PAIR_APPEASUSDC = '0x741d9c49400a727dfb120c791a88ea5a280da37e'   # Camelot USDC / apPEASUSDC
AP_PEAS = '0x6a02f704890f507f13d002f2785ca7ba5bfcc8f7'      # pod apPEAS (underlying PEAS)
AP_OHM = '0xeb1a8f8ea373536600082ba9ae2db97327513f7d'       # pod apOHM (underlying OHM)
PAIR_APPEAS_APOHM = '0x04d30065d2e6b1d83a163076935aefda4599c586'  # Camelot apPEAS / apOHM
PAIR_WETH_OHM = '0x8acd42e4b5a5750b44a28c5fb50906ebff145359'      # Camelot WETH / OHM
AP_UMP = '0xd9e2123ab94e2491eafa57d709a12ccf9c49b5ec'       # pod apUMP (bonded from OHM in the incumbent's take)
PAIR_PEAS_APUMP = '0x9f8a4f191ebb75e016f5edbba3e300bdd5106d49'    # Camelot PEAS / apUMP
PF_USDC = '0x3a87cf9af4d21778dad1ce7d0bf053f4b8f2631f'      # ERC4626 pfUSDC-6 (asset USDC)
PAIR_PFUSDC_PPEAS = '0x66fd4ae2c975706525d7bf29062d3eccb1349b9f'  # UNI-V2 pfUSDC-6 / pPEAS
AP_PMAX = '0xc3c802b97c7c9c0fed4b330be0ccd3b2d06f956d'      # pod apPmax (underlying PEAS)
PAIR_APPMAX_APOHM = '0x5384921c5bedaa760b58bede9594aadd5008283d'  # Camelot apPmax / apOHM
PAIR_USDC_APOHM = '0xe16270c27c2da345a42f01d0196a38590c8fd08e'    # Camelot USDC / apOHM
Z = '0x0000000000000000000000000000000000000000'
# Step = (kind, target, tokenIn, fee): 0 UniV3 swap, 1 V2 swap (fee in 1e5 units), 2 pod bond, 3 pod debond,
# 4 ERC4626 deposit, 5 ERC4626 redeem. Each step spends the executor's whole balance of tokenIn.
ROUTES = {
    'parb': [(0, PEAS_WETH, WETH, 0), (2, P_PEAS, PEAS, 0), (4, PF_PPEAS, P_PEAS, 0), (1, PAIR_PARB, PF_PPEAS, 300),
             (3, P_ARB, Z, 0), (0, ARB_WETH, ARB, 0)],
    'parb_rev': [(0, ARB_WETH, WETH, 0), (2, P_ARB, ARB, 0), (1, PAIR_PARB, P_ARB, 300), (5, PF_PPEAS, Z, 0),
                 (3, P_PEAS, Z, 0), (0, PEAS_WETH, PEAS, 0)],
    'appeasusdc': [(0, PEAS_WETH, WETH, 0), (2, AP_PEASUSDC, PEAS, 0), (1, PAIR_APPEASUSDC, AP_PEASUSDC, 300),
                   (0, WETH_USDC, USDC, 0)],
    'apohm': [(0, PEAS_WETH, WETH, 0), (2, AP_PEAS, PEAS, 0), (1, PAIR_APPEAS_APOHM, AP_PEAS, 300), (3, AP_OHM, Z, 0),
              (1, PAIR_WETH_OHM, OHM, 300)],
    'apump': [(1, PAIR_WETH_OHM, WETH, 300), (2, AP_UMP, OHM, 0), (1, PAIR_PEAS_APUMP, AP_UMP, 300),
              (0, PEAS_WETH, PEAS, 0)],
    'apump_rev': [(0, PEAS_WETH, WETH, 0), (1, PAIR_PEAS_APUMP, PEAS, 300), (3, AP_UMP, Z, 0),
                  (1, PAIR_WETH_OHM, OHM, 300)],
    'ppeas_usdc_rev': [(0, WETH_USDC, WETH, 0), (4, PF_USDC, USDC, 0), (1, PAIR_PFUSDC_PPEAS, PF_USDC, 300),
                       (3, P_PEAS, Z, 0), (0, PEAS_WETH, PEAS, 0)],
    'appmax': [(0, PEAS_WETH, WETH, 0), (2, AP_PMAX, PEAS, 0), (1, PAIR_APPMAX_APOHM, AP_PMAX, 300),
               (1, PAIR_USDC_APOHM, AP_OHM, 300), (0, WETH_USDC, USDC, 0)],
}
V3_SWAP = '0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67'   # cast keccak Swap(address,address,int256,int256,uint160,uint128,int24)
V2_SWAP = '0xd78ad95fa46c994b6551d0da85fc275fe613ce37657fb8d5e3d130840159d822'   # cast keccak Swap(address,uint256,uint256,uint256,uint256,address)
# Feed filters (2 of the 16 allowed on arbitrum; the PEAS/WETH one is shared with the trial's identical filter).
FILTERS = {
    'pool_swap': (PEAS_WETH, V3_SWAP),
    'pair_swap': (','.join([PAIR_PARB, PAIR_APPEASUSDC, PAIR_APPEAS_APOHM, PAIR_PEAS_APUMP, PAIR_PFUSDC_PPEAS,
                            PAIR_APPMAX_APOHM, PAIR_USDC_APOHM, PAIR_WETH_OHM]), V2_SWAP),
}
SEL_RUN = '0x4049437f'   # cast sig run(address,address,uint256,(uint8,address,address,uint32)[],uint256)
SEL_PROBE = '0x7f34303c'  # cast sig probe(address,address,uint256,(uint8,address,address,uint32)[][])
PROBE_GAS = 30_000_000   # eth_call only: eight reverted trials of about 1m gas each

PAPER_EXEC = '0xb464f7314d55ec6a9a0cf6f7f6df17af8ed5b352'   # fork deployment; paper code override only
PAPER_OWNER = '0xc0ffee0000000000000000000000000000000001'
EXEC = os.environ.get('EXECUTOR_ADDR_ARBITRUM') or os.environ.get('EXECUTOR_ADDR')
if MODE == 'live' and not EXEC:
    raise SystemExit('EXECUTOR_ADDR_ARBITRUM or EXECUTOR_ADDR is required in live mode')
RUNTIME = (HERE / 'executor-runtime.hex').read_text().strip()
if not RUNTIME.startswith('0x') or len(RUNTIME) < 100:
    raise SystemExit('missing paper executor runtime')

LOG = HERE / 'logs' / 'bot.jsonl'
STATE = HERE / 'state' / 'state.json'
CU_FILE = HERE / 'state' / 'cu.json'
LOG.parent.mkdir(exist_ok=True)
STATE.parent.mkdir(exist_ok=True)

# ---- loss guard -----------------------------------------------------------------------------
ETH_REF_USD = 4000.0           # deliberately high reference price for the USD cap (ETH is about 1,800)
MAX_TX_USD = 0.90              # signed gas cap (maxFee x gasLimit) at ETH_REF_USD stays under this
MAX_FEE_WEI = 100_000_000      # 0.1 gwei absolute ceiling for maxFeePerGas (base fee is 0.01-0.02 gwei)
MAX_GAS_LIMIT = 3_200_000      # live: 0.54m-1.44m used
GAS_MARGIN_NUM, GAS_MARGIN_DEN = 12, 10    # gas limit = eth_estimateGas x 1.20 + GAS_EXTRA
GAS_EXTRA = 600_000            # a pod transfer may also sell the pod's pending fees (fork: 0.905m used, 0.605m estimated)
BASE_FEE_HEADROOM_PCT = 5      # maxFeePerGas = latest base fee x 1.05 + TIP_WEI
TIP_WEI = 1                    # Arbitrum orders first come first served; a tip buys nothing. Never 0 (signer)
ROUGH_GAS = 1_300_000          # only for the cheap pre-filter before an estimate is made
TIMER_MILLI = 4                # the timer's single probe size, in 0.001 WETH
EVENT_MILLI = (4, 6, 10)       # sizes probed in parallel on a swap event (the trial's wins: 4, 4, 6, 6, 10)
EST_MILLI = 4                  # size of the gas estimates started with the probes; the limit adds 20 pct + 600k on top,
                               # and a send at 6 or 10 that still ran out of gas would only revert (gas, inside the cap)
POLL_INTERVAL = 120            # safety timer; all 10 live opportunities of the trial came from the feed, none from its timer
MIN_TRIGGER_GAP = 0.3          # seconds between two event-triggered checks (trial: 5); takes cascade block after block
SEND_COOLDOWN = 5              # per route (trial: 20)
RELAY_CU_CAP = 250_000         # per UTC day; the feed's own CU is metered separately
CU_COST = {'eth_call': 26, 'eth_estimateGas': 20, 'eth_getLogs': 75, 'eth_getTransactionReceipt': 20,
           'eth_blockNumber': 10, 'eth_getBlockByNumber': 20}
_id = 0
_cu_lock = threading.Lock()
_log_lock = threading.Lock()
POOL = concurrent.futures.ThreadPoolExecutor(max_workers=12)


class ReadBudgetExceeded(Exception):
    pass


def log(ev, **kw):
    row = {'ts': round(time.time(), 3), 'ev': ev, **kw}
    with _log_lock:
        with LOG.open('a') as f:
            f.write(json.dumps(row, separators=(',', ':'), default=str) + '\n')


def rpc(method, params):
    global _id
    with _cu_lock:
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
        rid = _id
    body = json.dumps({'jsonrpc': '2.0', 'id': rid, 'method': method, 'params': params}).encode()
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


def bot_address():
    import farmbot_signer
    a = farmbot_signer.my_address()
    a = a.get('address') if isinstance(a, dict) else a   # my_address() returns {"ok":..., "address":...}
    if not isinstance(a, str) or len(a) != 42:
        raise RuntimeError('signer my_address returned no address')
    return a


_ctx = None


def exec_ctx():
    """(from, executor, state override). The signer address is asked once and kept: one round trip less per check."""
    global _ctx
    if _ctx is None:
        if MODE == 'live':
            _ctx = (bot_address(), EXEC, None)
        else:
            _ctx = (PAPER_OWNER, PAPER_EXEC, {PAPER_EXEC: {'code': RUNTIME}})
    return _ctx


def calldata(route, amount_wei, min_profit):
    """ABI encoding of run(vault, weth, amount, Step[], minProfit); Step is a static 4-word tuple (checked against cast)."""
    steps = ROUTES[route]
    return (SEL_RUN + aword(VAULT) + aword(WETH) + word(amount_wei) + word(5 * 32) + word(min_profit)
            + word(len(steps)) + ''.join(word(k) + aword(t) + aword(i) + word(f) for k, t, i, f in steps))


def probe_calldata(amount_wei):
    """ABI encoding of probe(vault, weth, amount, Step[][]) over every route (checked against cast in selftest.py)."""
    inner = [word(len(steps)) + ''.join(word(k) + aword(t) + aword(i) + word(f) for k, t, i, f in steps)
             for steps in ROUTES.values()]
    offsets, pos = [], len(inner) * 32
    for x in inner:
        offsets.append(word(pos))
        pos += len(x) // 2
    return (SEL_PROBE + aword(VAULT) + aword(WETH) + word(amount_wei) + word(4 * 32)
            + word(len(inner)) + ''.join(offsets) + ''.join(inner))


def probe_all(ctx, milli):
    """One eth_call: the executor tries every route at one size and reverts each trial. {route: gain (0 = none)}."""
    frm, to, ov = ctx
    params = [{'from': frm, 'to': to, 'data': probe_calldata(milli * 10**15), 'gas': hex(PROBE_GAS)}, 'latest']
    raw = rpc('eth_call', params + ([ov] if ov else []))[2:]
    n = int(raw[64:128], 16)
    if n != len(ROUTES):
        raise RuntimeError(f'probe returned {n} gains for {len(ROUTES)} routes')
    return {route: int(raw[128 + 64 * i: 192 + 64 * i], 16) for i, route in enumerate(ROUTES)}


def base_fee():
    return int(rpc('eth_getBlockByNumber', ['latest', False])['baseFeePerGas'], 16)


def sim(data, ctx, gas):
    frm, to, ov = ctx
    params = [{'from': frm, 'to': to, 'data': data, 'gas': hex(gas)}, 'latest'] + ([ov] if ov else [])
    return int(rpc('eth_call', params)[2:66], 16)


def estimate(data, ctx):
    frm, to, ov = ctx
    params = [{'from': frm, 'to': to, 'data': data}, 'latest'] + ([ov] if ov else [])
    return int(rpc('eth_estimateGas', params), 16)


def winner_block(send_block, our_hash):
    """Block and tx of the last PEAS/WETH pool swap up to our block (ours if we won): every route swaps there."""
    logs = rpc('eth_getLogs', [{'address': PEAS_WETH, 'fromBlock': hex(max(0, send_block - 400)), 'toBlock': hex(send_block),
                                'topics': [V3_SWAP]}])
    ours = [int(x['blockNumber'], 16) for x in logs if x['transactionHash'].lower() == our_hash.lower()]
    if ours:
        return min(ours), None
    if not logs:
        return None, None
    last = max(logs, key=lambda x: (int(x['blockNumber'], 16), int(x['logIndex'], 16)))
    return int(last['blockNumber'], 16), last['transactionHash']


def send_live(route, data, gas_limit, max_fee, gross, min_profit, cap_wei, amount, timing):
    import farmbot_signer
    reply = farmbot_signer.send(CHAIN, EXEC, data, 0, gas_limit, max_fee, max_priority_fee_per_gas=TIP_WEI)
    timing['signed_s'] = round(time.time() - timing['t0'], 3)
    h = None
    if isinstance(reply, dict):
        h = reply.get('txHash') or reply.get('tx_hash') or reply.get('hash')
    if not h:
        log('signer_reject', reply=reply, route=route, amount_wei=amount)   # final, never retried
        return
    log('send', hash=h, route=route, amount_wei=amount, gas_limit=gas_limit, max_fee=max_fee, priority=TIP_WEI,
        gross_wei=gross, min_profit_wei=min_profit, gas_cap_wei=cap_wei, executor=EXEC, timing=timing)
    # the receipt is awaited off the main thread, so a second route that pays in the same look is signed at once
    threading.Thread(target=send_result, args=(h, route, gross, amount, timing), daemon=True).start()


def send_result(h, route, gross, amount, timing):
    try:
        _send_result(h, route, gross, amount, timing)
    except Exception as e:
        log('send_result', hash=h, route=route, result='unknown', error=str(e)[:160])


def _send_result(h, route, gross, amount, timing):
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
        log('send_result', hash=h, route=route, result='unknown', gas_used=None, winner_block=None)
        return
    b = int(receipt['blockNumber'], 16)
    status = int(receipt['status'], 16)
    used = int(receipt['gasUsed'], 16)
    cost = used * int(receipt['effectiveGasPrice'], 16)
    try:
        wb, wtx = winner_block(b, h)
    except Exception:
        wb, wtx = None, None
    log('send_result', hash=h, route=route, result='won' if status else 'lost', gas_used=used, gas_cost_wei=cost,
        send_block=b, winner_block=wb, winner_tx=wtx, blocks_after_winner=(b - wb if wb is not None else None),
        event_block=timing.get('event_block'), blocks_after_event=(b - timing['event_block'] if timing.get('event_block') else None),
        expected_gross_wei=gross, net_wei=(gross - cost if status else -cost), amount_wei=amount, trigger=timing.get('trigger'))


def take(s, route, size, gross, sweep, fee, timing, ctx, est_f=None):
    """A route shows a gain: gas estimate, cap, then sign. The executor's minProfit is the guard."""
    now = time.time()
    amount = size * 10**15
    max_fee = fee + fee * BASE_FEE_HEADROOM_PCT // 100 + TIP_WEI
    if gross <= ROUGH_GAS * max_fee * 8 // 10:
        log('check', trigger=timing['trigger'], route=route, gain_wei=gross, base_fee=fee, reason='gain_below_gas')
        return
    if s.setdefault('cooldown', {}).get(route, 0) > now:
        log('opportunity_skip', route=route, reason='cooldown')
        return
    try:
        # event: the estimate was started together with the probes (at EST_MILLI); timer: it is made now.
        # It reverts when the gain is already gone.
        est = est_f.result() if est_f else estimate(calldata(route, amount, 1), ctx)
    except ReadBudgetExceeded:
        raise
    except Exception as e:
        log('opportunity_skip', route=route, reason='estimate_revert', error=str(e)[:160], amount_wei=amount, gross_wei=gross,
            sweep=sweep, timing=dict(timing, estimate_s=round(time.time() - timing['t0'], 3)))
        return
    timing = dict(timing, estimate_s=round(time.time() - timing['t0'], 3))
    gas_limit = est * GAS_MARGIN_NUM // GAS_MARGIN_DEN + GAS_EXTRA
    cap_wei = gas_limit * max_fee
    cap_usd = cap_wei / 1e18 * ETH_REF_USD
    min_profit = cap_wei + 1                     # a win always pays more than the signed gas cap
    row = dict(trigger=timing['trigger'], route=route, sweep=sweep, amount_wei=amount, gross_wei=gross, base_fee=fee,
               gas_estimate=est, gas_limit=gas_limit, max_fee=max_fee, priority=TIP_WEI, gas_cap_wei=cap_wei,
               gas_cap_usd_at_ref=cap_usd, min_profit_wei=min_profit, timing=timing)
    if max_fee > MAX_FEE_WEI or gas_limit > MAX_GAS_LIMIT or cap_usd >= MAX_TX_USD:
        log('opportunity', **row)
        log('opportunity_skip', route=route, reason='fee_gas_or_usd_cap', max_fee=max_fee, gas_limit=gas_limit,
            gas_cap_usd_at_ref=cap_usd)
        return
    if gross <= cap_wei:
        log('opportunity', **row)
        log('opportunity_skip', route=route, reason='gross_below_gas_cap', gross_wei=gross, gas_cap_wei=cap_wei)
        return
    data = calldata(route, amount, min_profit)
    s['cooldown'][route] = now + SEND_COOLDOWN
    if MODE == 'live':
        # no second simulation: the estimate just ran this call, and run() reverts NoProfit below min_profit
        send_live(route, data, gas_limit, max_fee, gross, min_profit, cap_wei, amount, timing)
        log('opportunity', **row)
        return
    log('opportunity', **row)
    try:
        checked = sim(data, ctx, gas_limit)      # paper only: what the signed call would have returned
    except RuntimeError as e:
        log('paper_sim', result='revert', route=route, amount_wei=amount, min_profit_wei=min_profit, error=str(e)[:160])
        return
    log('paper_sim', result='success', route=route, amount_wei=amount, gross_wei=checked, min_profit_wei=min_profit,
        gas_limit=gas_limit, max_fee=max_fee, priority=TIP_WEI, gas_cap_wei=cap_wei, net_wei_at_cap=checked - cap_wei,
        timing=timing)


def check(s, trigger, event_block=None, t0=None):
    """One look at the chain. Timer: one probe. Swap event: three probe sizes, the base fee and a gas estimate per
    route, all started at once (one relay round trip), so a route that pays can be signed right after."""
    t0 = t0 or time.time()
    s['last_check'] = time.time()
    ctx = exec_ctx()
    event = trigger != 'timer'
    sizes = EVENT_MILLI if event else (TIMER_MILLI,)
    futs = {m: POOL.submit(probe_all, ctx, m) for m in sizes}
    fee_f = POOL.submit(base_fee) if event else None
    est_fs = {r: POOL.submit(estimate, calldata(r, EST_MILLI * 10**15, 1), ctx) for r in ROUTES} if event else {}
    by_size = {m: f.result() for m, f in futs.items()}
    best = {}                                    # route -> (size, gain, {size: gain})
    for route in ROUTES:
        sweep = {m: by_size[m][route] for m in sizes}
        m = max(sweep, key=sweep.get)
        if sweep[m]:
            best[route] = (m, sweep[m], sweep)
    if not best:
        if fee_f:
            fee_f.result()
        log('check', trigger=trigger, sizes=list(sizes), event_block=event_block, reason='nothing_to_take',
            probe_s=round(time.time() - t0, 3))
        return
    fee = fee_f.result() if fee_f else base_fee()
    timing = {'t0': t0, 'trigger': trigger, 'event_block': event_block, 'probe_s': round(time.time() - t0, 3)}
    for route, (m, gain, sweep) in sorted(best.items(), key=lambda x: -x[1][1]):
        take(s, route, m, gain, sweep, fee, timing, ctx, est_fs.get(route))


def load_state():
    try:
        return json.loads(STATE.read_text())
    except Exception:
        return {'last_check': 0, 'cooldown': {}}


def save_state(s):
    tmp = STATE.with_suffix('.tmp')
    tmp.write_text(json.dumps(s, separators=(',', ':')))
    tmp.replace(STATE)


EVENTS = queue.Queue()


def feed_loop(name):
    """One long-poll per filter; pushes (name, newest block, gap, receive time). No relay reads here."""
    address, topic0 = FILTERS[name]
    cursor = None
    while True:
        try:
            q = {'address': address, 'topic0': topic0, 'timeout': '55'}
            if cursor:
                q['after'] = cursor
            with urllib.request.urlopen(FEED + '?' + urllib.parse.urlencode(q), timeout=70) as r:
                result = json.load(r)
            cursor = result.get('cursor', cursor)
            logs = result.get('logs') or []
            if result.get('gap') or logs:
                blocks = []
                for x in logs:
                    try:
                        bn = x.get('blockNumber')
                        blocks.append(int(bn, 16) if isinstance(bn, str) else int(bn))
                    except Exception:
                        pass
                EVENTS.put((name, max(blocks) if blocks else None, bool(result.get('gap')), time.time()))
        except Exception as e:   # 429 / 503 / timeout: the safety timer keeps re-reading state
            log('feed_error', filter=name, error=str(e)[:180])
            EVENTS.put((name, None, True, time.time()))
            time.sleep(30)


def main():
    s = load_state()
    log('start', mode=MODE, executor=(EXEC if MODE == 'live' else PAPER_EXEC), filters={k: v[0] for k, v in FILTERS.items()},
        routes=list(ROUTES), poll_seconds=POLL_INTERVAL, event_sizes_milli=list(EVENT_MILLI))
    for name in FILTERS:
        threading.Thread(target=feed_loop, args=(name,), daemon=True).start()
    while True:
        try:   # every relay read, the first one included, happens inside this handler
            wait = POLL_INTERVAL - (time.time() - s.get('last_check', 0))
            if wait <= 0:
                check(s, 'timer')
                save_state(s)
                continue
            try:
                name, block, gap, t0 = EVENTS.get(timeout=max(0.05, min(55.0, wait)))
            except queue.Empty:
                continue
            if time.time() - s.get('last_check', 0) < MIN_TRIGGER_GAP:
                continue
            if time.time() - t0 > 3:      # a stale queued event: the state it pointed at was already read
                continue
            check(s, name + ('_gap' if gap else ''), block, t0)
        except ReadBudgetExceeded as e:
            log('read_budget', error=str(e))
            now = datetime.datetime.now(datetime.timezone.utc)
            midnight = (now + datetime.timedelta(days=1)).replace(hour=0, minute=0, second=5, microsecond=0)
            time.sleep(max(60, (midnight - now).total_seconds()))
        except Exception as e:
            log('loop_error', error=str(e)[:250])
            time.sleep(5)
        save_state(s)


if __name__ == '__main__':
    main()
