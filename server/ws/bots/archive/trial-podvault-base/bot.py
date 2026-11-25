"""trial-podvault-base: Peapods pods paired against lending-vault shares on Base, one atomic executor call.

Three Peapods pods on Base trade in a Uniswap V2 pair against an ERC4626 lending-vault share instead of a plain token:
pPEAS / pfWETH-12 (vault on WETH), pTibbeas / pfpPEAS-186 and pBTC.pLeasE / pfpPEAS-145 (vaults on pPEAS). When PEAS,
TIBBIR or the pair itself moves, a round trip WETH -> ... -> WETH through the vault's deposit / redeem, the pair, the
pod's bond / debond and the PEAS/USDC and WETH/USDC pools pays. The 0xc0ffee... executors take most of it within a
block or two (README); the bot aims at what is left seconds later. It waits on the feed for a Swap of the Uniswap V3
PEAS/USDC pool (and on a 60 s timer), simulates the executor's probe() for every route, sweeps the size when a route
shows a gain, and, when the simulated WETH gain exceeds the signed gas cap, sends it (BOT_MODE=live) or logs a paper
simulation (BOT_MODE=paper). The executor reverts unless its WETH balance grows by minProfit after the flash loan is
repaid, so a lost attempt costs gas only.
"""
import datetime
import json
import os
import sys
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
CHAIN = 'base'
FEED = 'http://127.0.0.1:8546/logs/base'

# Addresses: read from the incumbents' takes (scratch/r1805/steps.py on their receipts) and checked with
# token0()/token1()/factory()/fee()/asset() getters (scratch/trial-podvault-base/facts.py, facts.json), see README.
VAULT = '0xba12222222228d8ba445958a75a0704d566bf2c8'        # Balancer V2 Vault, flash loan fee 0
WETH = '0x4200000000000000000000000000000000000006'
PEAS = '0x02f92800f57bcd74066f5709f1daa1a4302df875'
USDC = '0x833589fcd6edb6e08f4c7c32d4f71b54bda02913'
WETH_USDC = '0xb4cb800910b228ed3d0834cf79d697127bbb00e5'      # Uniswap V3 WETH/USDC 0.01 pct
PEAS_USDC_SLIP = '0xb0a65b3a6f9da0e5eb057e0d5327deddbe17309e' # Aerodrome Slipstream PEAS/USDC (tick spacing 200)
PEAS_USDC_UNI = '0x8f8184bb6d3817910bc2ef91a393d2fe3ca8d774'  # Uniswap V3 PEAS/USDC 1 pct: the pool the CoW TWAP order trades on
PEAS_USDC = PEAS_USDC_UNI                                     # feed filter (shared with trial-podcycle-base) and winner lookup
P_PEAS = '0x9dbf562a65590c03e5400854d498844915c25944'         # pod pPEAS (underlying PEAS)
PF_WETH12 = '0x23574154842bc86cf5bbc5f99376cfa1e2f82497'      # pfWETH-12: Peapods lending vault share, ERC4626 on WETH
PAIR_PFW_PPEAS = '0x8444c479777e9662eeec4a301349be26e90c64de' # Uniswap V2 pfWETH-12 / pPEAS, fee 30 bps
P_TIB = '0x35ed7afef147857fc4d1b64fcb98b64e107145c3'          # pod pTibbeas (underlying TIBBIR)
TIBBIR = '0xa4a2e2ca3fbfe21aed83471d28b6f65a233c6e00'
PFP_PEAS186 = '0xa6ddb3c027c9882780a4c1544a93757674b9f393'    # pfpPEAS-186: lending vault share, ERC4626 on pPEAS
PAIR_PTIB_PFP = '0xd2bd8d1b22ddc1befbf888d90f98f20a6761ac64'  # Uniswap V2 pTibbeas / pfpPEAS-186, fee 30 bps
SLIP_WETH_TIB = '0x0f664affb82f074937d5cfcd61b97f3f32d5dc50'  # Aerodrome Slipstream WETH / TIBBIR (tick spacing 200)
P_BTC = '0x7a148e0711beaaeeb8fe569877b21ff6c22f126b'          # pod pBTC.pLeasE (underlying cbBTC)
CBBTC = '0xcbb7c0000ab88b473b1f5afd9ef808440eed33bf'
PFP_PEAS145 = '0xbf93c406a7d36da1facc2dbc6809be75c119cd7b'    # pfpPEAS-145: lending vault share, ERC4626 on pPEAS
PAIR_PBTC_PFP = '0x287fdd1cffec8e6f8773e2c8eba757eb8605cc99'  # Uniswap V2 pBTC.pLeasE / pfpPEAS-145, fee 30 bps
V3_WETH_CBBTC = '0x7aea2e8a3843516afa07293a10ac8e49906dabd1'  # Uniswap V3 WETH / cbBTC 0.05 pct (factory getPool)
Z = '0x0000000000000000000000000000000000000000'
# Step = (kind, target, tokenIn, fee): 0 UniV3-style swap, 1 V2-style swap (fee in 1e5 units), 2 pod bond, 3 pod debond,
# 4 ERC4626 deposit, 5 ERC4626 redeem. Each step spends the executor's whole balance of tokenIn.
ROUTES = {
    # WETH -> pfWETH-12 (deposit) -> pPEAS (pair) -> debond PEAS -> USDC -> WETH (incumbents 0x0b725e38, 0x5817c0e2, 0x0d42f51a)
    'pfw_fwd': [(4, PF_WETH12, WETH, 0), (1, PAIR_PFW_PPEAS, PF_WETH12, 300), (3, P_PEAS, Z, 0), (0, PEAS_USDC_SLIP, PEAS, 0),
                (0, WETH_USDC, USDC, 0)],
    # the mirror: WETH -> USDC -> PEAS -> bond pPEAS -> pfWETH-12 (pair) -> redeem WETH (incumbent 0x26532d44)
    'pfw_rev': [(0, WETH_USDC, WETH, 0), (0, PEAS_USDC_SLIP, USDC, 0), (2, P_PEAS, PEAS, 0), (1, PAIR_PFW_PPEAS, P_PEAS, 300),
                (5, PF_WETH12, Z, 0)],
    # WETH -> TIBBIR -> bond pTibbeas -> pfpPEAS-186 (pair) -> redeem pPEAS -> debond PEAS -> USDC -> WETH (incumbent 0x96b2f4fc)
    'tib_fwd': [(0, SLIP_WETH_TIB, WETH, 0), (2, P_TIB, TIBBIR, 0), (1, PAIR_PTIB_PFP, P_TIB, 300), (5, PFP_PEAS186, Z, 0),
                (3, P_PEAS, Z, 0), (0, PEAS_USDC_SLIP, PEAS, 0), (0, WETH_USDC, USDC, 0)],
    # the mirror (incumbents 0x85f251b0, 0x25b1787c)
    'tib_rev': [(0, WETH_USDC, WETH, 0), (0, PEAS_USDC_SLIP, USDC, 0), (2, P_PEAS, PEAS, 0), (4, PFP_PEAS186, P_PEAS, 0),
                (1, PAIR_PTIB_PFP, PFP_PEAS186, 300), (3, P_TIB, Z, 0), (0, SLIP_WETH_TIB, TIBBIR, 0)],
    # WETH -> cbBTC -> bond pBTC.pLeasE -> pfpPEAS-145 (pair) -> redeem pPEAS -> debond PEAS -> USDC -> WETH (incumbent 0x5b855858)
    'btc_fwd': [(0, V3_WETH_CBBTC, WETH, 0), (2, P_BTC, CBBTC, 0), (1, PAIR_PBTC_PFP, P_BTC, 300), (5, PFP_PEAS145, Z, 0),
                (3, P_PEAS, Z, 0), (0, PEAS_USDC_SLIP, PEAS, 0), (0, WETH_USDC, USDC, 0)],
    # the mirror (incumbents 0x11c2e636, 0xe3722497)
    'btc_rev': [(0, WETH_USDC, WETH, 0), (0, PEAS_USDC_SLIP, USDC, 0), (2, P_PEAS, PEAS, 0), (4, PFP_PEAS145, P_PEAS, 0),
                (1, PAIR_PBTC_PFP, PFP_PEAS145, 300), (3, P_BTC, Z, 0), (0, V3_WETH_CBBTC, CBBTC, 0)],
}
SWAP_TOPIC = '0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67'     # Swap of Uniswap V3 and Slipstream pools
SEL_RUN = '0x4049437f'   # cast sig run(address,address,uint256,(uint8,address,address,uint32)[],uint256)
SEL_PROBE = '0x7f34303c'  # cast sig probe(address,address,uint256,(uint8,address,address,uint32)[][])
PROBE_GAS = 30_000_000   # eth_call only: six reverted trials of about 1m-1.6m gas each

PAPER_EXEC = '0xb464f7314d55ec6a9a0cf6f7f6df17af8ed5b352'   # fork deployment; paper code override only
PAPER_OWNER = '0xc0ffee0000000000000000000000000000000001'
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

# ---- loss guard -----------------------------------------------------------------------------
# Base is an OP Stack chain: the L1 data fee and the operator fee are charged at inclusion and no signed field bounds
# them, so the only enforceable worst case of one send is the bot wallet's native balance. The trial limit is 1 USD
# per send, therefore the wallet itself stays under 1 USD: the manifest funds 0.75 USD, and take() refuses to sign
# while balance x ETH/USD is WALLET_MAX_USD or more (review 57f67367, 2026-11-19).
WALLET_MAX_USD = 0.95          # live: no send while the bot wallet's native balance is worth this much or more
SEL_SLOT0 = '0x3850c7bd'       # cast sig slot0(); read on WETH_USDC (token0 = WETH, token1 = USDC) for ETH/USD
ETH_USD_MIN, ETH_USD_MAX = 300.0, 20000.0   # a pool price outside this band is treated as unreadable: no send
ETH_REF_USD = 4000.0           # deliberately high reference price for the signed-cap check (ETH is about 1,800)
MAX_TX_USD = 0.90              # signed gas cap (maxFee x gasLimit + L1 allowance) at ETH_REF_USD stays under this
MAX_FEE_WEI = 100_000_000      # 0.1 gwei absolute ceiling for maxFeePerGas (base fee is 0.005 gwei)
MAX_GAS_LIMIT = 3_200_000      # fork: 0.6m-1.6m used; a take that needs more is skipped
SIM_GAS = 3_200_000
GAS_MARGIN_NUM, GAS_MARGIN_DEN = 12, 10    # gas limit = eth_estimateGas x 1.20 + GAS_EXTRA
GAS_EXTRA = 600_000            # a pod transfer may also sell the pod's pending fees into its pair
BASE_FEE_HEADROOM_PCT = 5      # maxFeePerGas = latest base fee x 1.05 + tip
# Base orders a block by priority fee and the incumbents bid 0.001-0.1 gwei, more for bigger gains (README).
# The bot bids at most TIP_SHARE_PCT of the simulated gross, spread over the gas limit, within [MIN_TIP, MAX_TIP].
TIP_SHARE_PCT = 20
MIN_TIP_WEI = 100_000          # 0.0001 gwei; never 0 (the signer would replace 0 by maxFee / 10)
MAX_TIP_WEI = 50_000_000       # 0.05 gwei
L1_ALLOWANCE_WEI = 100_000_000_000   # OP Stack L1 data fee, not bounded by the signed fields: incumbents paid about 1e9 wei
ROUGH_GAS = 1_000_000          # only for the cheap pre-filter before an estimate is made
PROBE_MILLI = 1                # probe size in 0.001 WETH
SIZES_MILLI = (1, 2, 4, 8, 16) # flash-borrowed WETH, never the bot's own funds (the pairs hold 0.1-0.2 WETH a side)
POLL_INTERVAL = 60             # safety timer: one probe() eth_call (26 CU) every 60 s = 1,440 x 26 = 37,440 CU/day
FEED_ENABLED = True            # feed /logs/base: Swap of the Uniswap V3 PEAS/USDC pool 0x8f8184bb (about 400 logs/day; the
                               # same filter trial-podcycle-base already holds); 429/503/gap fall back to the timer
MIN_TRIGGER_GAP = 3            # seconds between two feed-triggered checks
SEND_COOLDOWN = 20             # per route
RELAY_CU_CAP = 90_000          # per UTC day; the feed's own CU is metered separately
CU_COST = {'eth_call': 26, 'eth_estimateGas': 20, 'eth_getLogs': 75, 'eth_getTransactionReceipt': 20,
           'eth_blockNumber': 10, 'eth_getBlockByNumber': 20, 'eth_getBalance': 20}
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


def probe_all(ctx):
    """One eth_call: the executor tries every route at the probe size and reverts each trial. {route: gain or None}."""
    frm, to, ov = ctx
    params = [{'from': frm, 'to': to, 'data': probe_calldata(PROBE_MILLI * 10**15), 'gas': hex(PROBE_GAS)}, 'latest']
    raw = rpc('eth_call', params + ([ov] if ov else []))[2:]
    n = int(raw[64:128], 16)
    if n != len(ROUTES):
        raise RuntimeError(f'probe returned {n} gains for {len(ROUTES)} routes')
    gains = [int(raw[128 + 64 * i: 192 + 64 * i], 16) for i in range(n)]
    return {route: (g or None) for route, g in zip(ROUTES, gains)}


def sim(data, ctx, gas=SIM_GAS):
    frm, to, ov = ctx
    params = [{'from': frm, 'to': to, 'data': data, 'gas': hex(gas)}, 'latest'] + ([ov] if ov else [])
    return int(rpc('eth_call', params)[2:66], 16)


def try_sim(data, ctx, gas=SIM_GAS):
    try:
        return sim(data, ctx, gas)
    except ReadBudgetExceeded:
        raise
    except RuntimeError:
        return None    # executor revert: the round trip does not pay


def estimate(data, ctx):
    frm, to, ov = ctx
    params = [{'from': frm, 'to': to, 'data': data}, 'latest'] + ([ov] if ov else [])
    return int(rpc('eth_estimateGas', params), 16)


def eth_usd():
    """USDC per WETH from slot0 of the Uniswap V3 WETH/USDC 0.01 pct pool (token0 WETH 18 dec, token1 USDC 6 dec)."""
    raw = rpc('eth_call', [{'to': WETH_USDC, 'data': SEL_SLOT0}, 'latest'])
    sqrt_p = int(raw[2:66], 16)
    price = sqrt_p * sqrt_p * 10**12 / 2**192
    if not ETH_USD_MIN < price < ETH_USD_MAX:
        raise RuntimeError(f'ETH/USD {price} outside the plausible band')
    return price


def wallet_bound(balance_wei, price, cap_wei):
    """The enforceable worst case of one send on an OP Stack chain is the wallet's native balance.
    Returns (ok, reason, balance_usd): ok only if the balance is worth less than WALLET_MAX_USD and covers the cap."""
    usd = balance_wei / 1e18 * price
    if usd >= WALLET_MAX_USD:
        return False, 'wallet_at_or_above_usd_bound', usd
    if balance_wei < cap_wei:
        return False, 'wallet_below_gas_cap', usd
    return True, None, usd


def winner_block(send_block, our_hash):
    """Block and tx of the last PEAS/USDC pool swap up to our block (ours if we won): every route swaps there."""
    logs = rpc('eth_getLogs', [{'address': PEAS_USDC, 'fromBlock': hex(max(0, send_block - 400)), 'toBlock': hex(send_block),
                                'topics': [SWAP_TOPIC]}])
    ours = [int(x['blockNumber'], 16) for x in logs if x['transactionHash'].lower() == our_hash.lower()]
    if ours:
        return min(ours), None
    if not logs:
        return None, None
    last = max(logs, key=lambda x: (int(x['blockNumber'], 16), int(x['logIndex'], 16)))
    return int(last['blockNumber'], 16), last['transactionHash']


def send_live(route, data, gas_limit, max_fee, tip, gross, min_profit, cap_wei, amount):
    import farmbot_signer
    reply = farmbot_signer.send(CHAIN, EXEC, data, 0, gas_limit, max_fee, max_priority_fee_per_gas=tip)
    h = None
    if isinstance(reply, dict):
        h = reply.get('txHash') or reply.get('tx_hash') or reply.get('hash')
    if not h:
        log('signer_reject', reply=reply, route=route, amount_wei=amount)   # final, never retried
        return
    log('send', hash=h, route=route, amount_wei=amount, gas_limit=gas_limit, max_fee=max_fee, priority=tip,
        gross_wei=gross, min_profit_wei=min_profit, gas_cap_wei=cap_wei, executor=EXEC)
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
    l1_fee = int(receipt.get('l1Fee') or '0x0', 16)
    cost = used * int(receipt['effectiveGasPrice'], 16) + l1_fee
    try:
        wb, wtx = winner_block(b, h)
    except Exception:
        wb, wtx = None, None
    log('send_result', hash=h, route=route, result='won' if status else 'lost', gas_used=used, gas_cost_wei=cost, l1_fee_wei=l1_fee,
        send_block=b, winner_block=wb, winner_tx=wtx, blocks_after_winner=(b - wb if wb is not None else None),
        expected_gross_wei=gross, net_wei=(gross - cost if status else -cost), amount_wei=amount)


def take(s, route, probe, trigger, ctx, now):
    """A route shows a gain at the probe size: sweep, cap, guard, then send or paper-log."""
    base_fee = int(rpc('eth_getBlockByNumber', ['latest', False])['baseFeePerGas'], 16)
    fee_floor = base_fee + base_fee * BASE_FEE_HEADROOM_PCT // 100 + MIN_TIP_WEI
    if probe <= ROUGH_GAS * fee_floor * 8 // 10:
        log('check', trigger=trigger, route=route, probe_gain_wei=probe, base_fee=base_fee, reason='gain_below_gas')
        return False
    rows = {PROBE_MILLI: probe}
    for size in SIZES_MILLI:
        if size != PROBE_MILLI:
            rows[size] = try_sim(calldata(route, size * 10**15, 1), ctx)
    size, gross = max(((k, v) for k, v in rows.items() if v), key=lambda x: x[1])
    amount = size * 10**15
    try:
        est = estimate(calldata(route, amount, 1), ctx)
    except RuntimeError as e:
        log('opportunity_skip', route=route, reason='estimate_revert', error=str(e)[:160], amount_wei=amount, gross_wei=gross)
        return False
    gas_limit = est * GAS_MARGIN_NUM // GAS_MARGIN_DEN + GAS_EXTRA
    tip = max(MIN_TIP_WEI, min(MAX_TIP_WEI, gross * TIP_SHARE_PCT // 100 // gas_limit))   # bid: at most 20 pct of gross
    max_fee = base_fee + base_fee * BASE_FEE_HEADROOM_PCT // 100 + tip
    cap_wei = gas_limit * max_fee + L1_ALLOWANCE_WEI   # expected ceiling of one send; the L1 allowance is an estimate, the bound is wallet_bound()
    cap_usd = cap_wei / 1e18 * ETH_REF_USD
    min_profit = cap_wei + 1                     # a win always pays more than the signed gas cap
    log('opportunity', trigger=trigger, route=route, sweep=rows, amount_wei=amount, gross_wei=gross, base_fee=base_fee,
        gas_estimate=est, gas_limit=gas_limit, max_fee=max_fee, priority=tip, gas_cap_wei=cap_wei,
        gas_cap_usd_at_ref=cap_usd, min_profit_wei=min_profit)
    if max_fee > MAX_FEE_WEI or gas_limit > MAX_GAS_LIMIT or cap_usd >= MAX_TX_USD:
        log('opportunity_skip', route=route, reason='fee_gas_or_usd_cap', max_fee=max_fee, gas_limit=gas_limit,
            gas_cap_usd_at_ref=cap_usd)
        return False
    if gross <= cap_wei:
        log('opportunity_skip', route=route, reason='gross_below_gas_cap', gross_wei=gross, gas_cap_wei=cap_wei)
        return False
    if s.setdefault('cooldown', {}).get(route, 0) > now:
        log('opportunity_skip', route=route, reason='cooldown')
        return False
    data = calldata(route, amount, min_profit)
    checked = try_sim(data, ctx, gas_limit)      # the exact guarded call at the signed gas limit
    if not checked:
        log('simulate_revert', route=route, amount_wei=amount, min_profit_wei=min_profit, gas_limit=gas_limit)
        return False
    # OP Stack loss bound: one send can cost at most the wallet's native balance, which must be worth under 1 USD.
    try:
        price = eth_usd()
    except RuntimeError as e:
        log('opportunity_skip', route=route, reason='eth_usd_unreadable', error=str(e)[:160])
        return False
    s['cooldown'][route] = now + SEND_COOLDOWN
    if MODE == 'live':
        balance = int(rpc('eth_getBalance', [ctx[0], 'latest']), 16)
        ok, reason, usd = wallet_bound(balance, price, cap_wei)
        if not ok:
            log('opportunity_skip', route=route, reason=reason, wallet_wei=balance, wallet_usd=usd, eth_usd=price,
                wallet_max_usd=WALLET_MAX_USD, gas_cap_wei=cap_wei)
            return False
        log('wallet_bound', route=route, wallet_wei=balance, wallet_usd=usd, eth_usd=price, wallet_max_usd=WALLET_MAX_USD)
        send_live(route, data, gas_limit, max_fee, tip, checked, min_profit, cap_wei, amount)
    else:
        log('paper_sim', result='success', route=route, amount_wei=amount, gross_wei=checked, min_profit_wei=min_profit,
            gas_limit=gas_limit, max_fee=max_fee, priority=tip, gas_cap_wei=cap_wei, net_wei_at_cap=checked - cap_wei,
            eth_usd=price, gas_cap_usd=cap_wei / 1e18 * price, wallet_max_usd=WALLET_MAX_USD)
    return True


def check(s, trigger):
    """One look at the chain: probe every route, act on those that show a gain."""
    now = time.time()
    s['last_check'] = now
    ctx = exec_ctx()
    probes = probe_all(ctx)
    live ={r: g for r, g in probes.items() if g}
    if not live:
        log('check', trigger=trigger, probes=probes, reason='nothing_to_take')
        return
    for route, gain in sorted(live.items(), key=lambda x: -x[1]):
        if take(s, route, gain, trigger, ctx, now):
            break    # one send per look: the routes share the WETH/USDC and PEAS/USDC legs, a second would revert


def load_state():
    try:
        return json.loads(STATE.read_text())
    except Exception:
        return {'feed_cursor': None, 'last_check': 0, 'cooldown': {}}


def save_state(s):
    tmp = STATE.with_suffix('.tmp')
    tmp.write_text(json.dumps(s, separators=(',', ':')))
    tmp.replace(STATE)


def feed_wait(cursor, timeout):
    q = {'address': PEAS_USDC, 'topic0': SWAP_TOPIC, 'timeout': str(timeout)}
    if cursor:
        q['after'] = cursor
    with urllib.request.urlopen(FEED + '?' + urllib.parse.urlencode(q), timeout=timeout + 10) as r:
        return json.load(r)


def main():
    s = load_state()
    log('start', mode=MODE, executor=(EXEC if MODE == 'live' else PAPER_EXEC), feed=FEED_ENABLED, feed_pool=PEAS_USDC,
        routes=list(ROUTES), poll_seconds=POLL_INTERVAL)
    while True:
        try:
            wait = POLL_INTERVAL - (time.time() - s.get('last_check', 0))
            if wait <= 0:
                check(s, 'timer')
                save_state(s)
                continue
            if not FEED_ENABLED:
                time.sleep(wait)
                continue
            # the feed long-poll is the sleep; a PEAS/USDC pool swap or a gap triggers a check at once
            result = feed_wait(s.get('feed_cursor'), max(1, min(55, int(wait) + 1)))
            s['feed_cursor'] = result.get('cursor', s.get('feed_cursor'))
            if result.get('gap') or result.get('logs'):
                if time.time() - s.get('last_check', 0) >= MIN_TRIGGER_GAP:
                    check(s, 'gap' if result.get('gap') else 'pool_swap')
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
            log('feed_error', error=str(e)[:180])   # 429/503/timeout: the timer keeps re-reading state
            time.sleep(min(30, max(1, POLL_INTERVAL - (time.time() - s.get('last_check', 0)))))
        except ReadBudgetExceeded as e:
            log('read_budget', error=str(e))
            time.sleep(600)
        except Exception as e:
            log('loop_error', error=str(e)[:250])
            time.sleep(5)
        save_state(s)


if __name__ == '__main__':
    main()
