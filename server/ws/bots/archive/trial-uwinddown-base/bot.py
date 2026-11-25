#!/usr/bin/env python3
"""Trial: Universal Protocol wind-down vault on Base, redeem price versus the uAsset's WETH pool.

Universal is winding down. Its UniversalWindDownVault (verified source) pays a fixed USDC rate per uAsset (uSOL,
uXRP, uDOGE, ...) to anyone who calls redeem(asset, amount, minUSDC); it burns the uAsset. The uAssets still trade
in Uniswap-V3-style pools against WETH, so every fall of ETH (or any sale into a pool) leaves a uAsset cheaper in
its pool than the vault pays. One transaction through the WindDownArb executor flash-borrows USDC from Morpho
Blue, swaps USDC -> WETH -> uAsset, redeems at the vault, repays and pays the USDC gain to the bot wallet. The
executor reverts unless the USDC balance grew by minProfit, so a lost attempt costs gas only.

The gap opens with the ETH price (no single event to wait on; the WETH/USDC pool's Swap is a busy event), so the
bot polls on a timer: one eth_call of the executor's scan() (every size of every route in one call) per POLL_S.
"""
import datetime
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
MODE = os.environ.get('BOT_MODE', 'paper')
LANE = os.environ.get('RPC_LANE', 'paper')
RELAY = os.environ['RPC_RELAY_URL'].rstrip('/')
CHAIN = 'base'

# Route targets: all are call arguments of the executor (measurement scratch/rf5f3, proof scratch/trial-uwinddown-base)
MORPHO = '0xbbbbbbbbbb9cc5e90e3b3af64bdaf62c37eeffcb'   # Morpho Blue on Base (flash lender, no fee)
WETH = '0x4200000000000000000000000000000000000006'
USDC = '0x833589fcd6edb6e08f4c7c32d4f71b54bda02913'     # 6 decimals
VAULT = '0x1f69bbf9f7ed316bcf1e0cf12f81d261a9bdc2ca'    # UniversalWindDownVault (Blockscout-verified)
P_IN = '0xd0b53d9277642d899df5c87a3966a349a798f224'     # Uniswap V3 WETH/USDC 0.05% (token0 WETH)
# name -> (uAsset, its WETH pool). Pools read from the incumbents' receipts; token0/token1 checked in scratch/rf5f3/wd_pools.py
ROUTES = {
    'uSOL': ('0x9b8df6e244526ab5f6e6400d331db28c8fdddb55', '0x0225ba893d5f8ecd6d2022f9dec59b34f61098a1'),
    'uSOL/2': ('0x9b8df6e244526ab5f6e6400d331db28c8fdddb55', '0xab04a352d4ec8d0f1812a4e5ebe7807fa67acd48'),
    'uSOL/3': ('0x9b8df6e244526ab5f6e6400d331db28c8fdddb55', '0x3055c02126af266490255d0350644f408c18e064'),
    'uSOL/4': ('0x9b8df6e244526ab5f6e6400d331db28c8fdddb55', '0xe6e4ebe393698c4d7b10dc122e54dcc19ffa042d'),
    'uDOGE': ('0x12e96c2bfea6e835cf8dd38a5834fa61cf723736', '0x84a8fedc7f310045c06be3f9e412e58ec82448b2'),
    'uADA': ('0xa3a34a0d9a08ccddb6ed422ac0a28a06731335aa', '0xd52ad625a19e5f258630413e374d65825d08e1df'),
    'uXRP': ('0x2615a94df961278dcbc41fb0a54fec5f10a693ae', '0xc8da14d7467814a91384796db3ca2c273b30b361'),
    'uXRP/2': ('0x2615a94df961278dcbc41fb0a54fec5f10a693ae', '0x61c6e9e93592e535efc1bee07f491a517e98f6d0'),
    'uNEAR': ('0x5ed25e305e08f58afd7995eac72563e6be65a617', '0x38e2e7dead99f8fc492081947031be43eaab13a5'),
    'uARB': ('0xd01cb4171a985571deff48c9dc2f6e153a244d64', '0xae50c3b3e9be6a836f2fe3c5c8daea5eafaf28b2'),
    'uSUI': ('0xb0505e5a99abd03d94a1169e638b78edfed26ea4', '0x5c45b0f48c326f79b56709d8f63ce2bee7697106'),
    'uLTC': ('0x3eb097375fc2fc361e4a472f5e7067238c547c52', '0xab7fed603f0e5eb8f46ab58b086631d75cfbe78d'),
    'uATOM': ('0x6e934283dae5d5d1831cbe8d557c44c9b83f30ee', '0x9330816bf6a27c1f149640d7ad3408cabc2eb576'),
    'uLINK': ('0xd403d1624daef243fbcbd4a80d8a6f36affe32b2', '0x8bbc52f056cbc6fe43f7e46183fef35577d5b217'),
    'uBTC': ('0xf1143f3a8d76f1ca740d29d5671d365f66c44ed1', '0xddf56af090c09bb0f993e00d7c676076cc59c72e'),
    'uZEC': ('0x83f31af747189c2fa9e5deb253200c505eff6ed2', '0x3054f64e28140ee00428be94eac4ad6f7241712a'),
    # uAssets no incumbent had arbitraged by 2026-11-20: Uniswap V3 getPool(asset, WETH, 3000), scratch/rf5f3/wd_more.py
    'uDOT': ('0x0f813f4785b2360009f9ac9bf6121a85f109efc6', '0xcb620881e671f2b2d5e233b3293c186f94d4100a'),
    'uXLM': ('0x378c326a472915d38b2d8d41e1345987835fab64', '0x9140d1bc4f976dbcea88575f42d73716054c38bd'),
    'uALGO': ('0x3a51f2a377ea8b55faf3c671138a00503b031af3', '0x81dc9e1151d9221b3197c4304b23736e900f87da'),
    'uSEI': ('0x71a67215a2025f501f386a49858a9ced2fc0249d', '0x5bf0621cc4c50e5491aa51dad02db8dd37e66b03'),
    'uBCH': ('0x7be0cc2cadcd4a8f9901b4a66244dcdd9bd02e0f', '0xfd2a49db3a5a2184be19cd130eeff4ed486fa77c'),
    'uHBAR': ('0xc79e06860aa9564f95e08fb7e5b61458d0c63898', '0x54f6fbbcfb730dbf31829fe4e2d8d769503be115'),
    'uAVAX': ('0xd6a34b430c05ac78c24985f8abee2616bc1788cb', '0x12122ec8f9211a34b228f349a2b6726bcd04554e'),
}
SIZES = [25, 150, 800, 4000]                   # USDC borrowed; every size of every route in one scan
REFINE = [0.4, 0.6, 0.8, 1.0, 1.3, 1.7, 2.2, 3.0]   # second scan around the best size of the best route
SIZE_MAX = 12000                               # USDC, the largest flash this bot ever asks for
GAS_ORACLE = '0x420000000000000000000000000000000000000f'   # OP Stack GasPriceOracle predeploy
SEL_RUN = '0x7bf0e18b'     # cast sig run((address,address,uint256,address,address,address,address,address,uint256,uint256))
SEL_SCAN = '0x6bcf3a77'    # cast sig scan((address,address,uint256,address,address,address,address,address,uint256,uint256)[])
SEL_SLOT0 = '0x3850c7bd'   # cast sig slot0()
SEL_L1UB = '0xf1c7a58b'    # cast sig getL1FeeUpperBound(uint256)
T_REDEEMED = '0x5cdf07ad0fc222442720b108e3ed4c4640f0fadc2ab2253e66f259a0fea83480'   # cast keccak Redeemed(address,address,uint256,uint256)

PAPER_EXEC = '0x8f7a45ebde059392e46a46dcc14ab24681a961ea'    # fork deployment; paper code override only
PAPER_OWNER = '0x1111111111111111111111111111111111111111'   # the owner baked into that deployment (immutable)
EXEC = os.environ.get('EXECUTOR_ADDR_BASE') or os.environ.get('EXECUTOR_ADDR')
if MODE == 'live' and not EXEC:
    raise SystemExit('EXECUTOR_ADDR_BASE or EXECUTOR_ADDR is required in live mode')
RUNTIME = (HERE / 'executor-runtime.hex').read_text().strip()
if not RUNTIME.startswith('0x'):
    raise SystemExit('missing paper executor runtime')
LOG = HERE / 'logs' / 'bot.jsonl'
CU_FILE = HERE / 'state' / 'cu.json'
LOG.parent.mkdir(exist_ok=True)
CU_FILE.parent.mkdir(exist_ok=True)

# ---- loss guard (trial rule: every send's gas limit x maxFeePerGas + L1 data fee < 1 USD) ----
GAS_LIMIT_MAX = 1_500_000
GAS_LIMIT_FALLBACK = 800_000   # used only if eth_estimateGas fails (paper); live never sends without an estimate
GAS_MARGIN = 1.3               # a take uses about 520k gas (fork), a late revert about 575-640k
SEND_CAP_USD = 0.95            # gas limit x maxFeePerGas + L1 fee bound, at the pool ETH price x 1.15, stays under this
ETH_MARGIN = 1.15
BID_SHARE = 0.35               # priority fee bid is at most 35% of simulated gross
GAIN_OVER_CAP = 1.2            # send only if the simulated gain is at least 1.2 x this send's gas cap
MIN_GAIN_USDC = 30_000         # 0.03 USDC: smaller scan gains are not evaluated at all
TX_BYTES = 480                 # run() calldata is 324 bytes; the signed tx stays under 480
POLL_S = 27                    # one scan eth_call per poll: 3,200 polls/day x 26 CU = 83,200 CU
PRICE_TTL_S = 900
COOLDOWN_S = 5                 # after a send, before the next poll
SKIP_S = 120                   # a route that was evaluated and skipped (or paper-simulated) is not re-evaluated for this long
CU_COST = {'eth_call': 26, 'eth_getLogs': 75, 'eth_getTransactionReceipt': 20, 'eth_blockNumber': 10,
           'eth_gasPrice': 10, 'eth_estimateGas': 26}
CU_CAP = 98_000                # relay CU/day, hard cap in code (trial rule: <= 100,000)
_id = 0
_price = {'ts': 0.0, 'usd': 0.0}
_skip = {}


class ReadBudgetExceeded(Exception):
    pass


def log(ev, **kw):
    row = {'ts': time.time(), 'ev': ev, **kw}
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
    if budget['cu'] + cost > CU_CAP:
        raise ReadBudgetExceeded(f'{CU_CAP} relay CU/day bot cap reached')
    budget['cu'] += cost
    CU_FILE.write_text(json.dumps(budget))
    _id += 1
    body = json.dumps({'jsonrpc': '2.0', 'id': _id, 'method': method, 'params': params}).encode()
    req = urllib.request.Request(f'{RELAY}/{CHAIN}?lane={LANE}', body, {'content-type': 'application/json'})
    with urllib.request.urlopen(req, timeout=30) as resp:
        ans = json.load(resp)
    if 'error' in ans:
        raise RuntimeError(f'{method}: {ans["error"]}')
    return ans['result']


def word(n):
    return format(n, '064x')


def aw(a):
    return a.lower().removeprefix('0x').zfill(64)


def enc_params(route, amount, min_profit, deadline):
    """Params = (morpho, usdc, amount, mid, poolIn, asset, poolAsset, vault, minProfit, deadline): 10 static words."""
    asset, pool = ROUTES[route]
    return (aw(MORPHO) + aw(USDC) + word(amount) + aw(WETH) + aw(P_IN) + aw(asset) + aw(pool) + aw(VAULT)
            + word(min_profit) + word(deadline))


def run_data(route, amount, min_profit, deadline):
    return SEL_RUN + enc_params(route, amount, min_profit, deadline)


def scan_data(cands, deadline):
    return SEL_SCAN + word(32) + word(len(cands)) + ''.join(enc_params(r, a, 0, deadline) for r, a in cands)


# candidates: every size on every route, one scan call (amounts in USDC units)
CANDS = [(r, int(s * 1e6)) for r in ROUTES for s in SIZES]


def signer():
    sys.path.append('/opt/farm/lib')
    import farmbot_signer
    return farmbot_signer


def owner():
    a = signer().my_address()
    a = a['address'] if isinstance(a, dict) else a
    if not isinstance(a, str) or len(a) != 42:
        raise RuntimeError('signer my_address returned no address')
    return a


def ctx():
    """(from, executor, state override list) for this mode."""
    if MODE == 'live':
        return owner(), EXEC, []
    return PAPER_OWNER, PAPER_EXEC, [{PAPER_EXEC: {'code': RUNTIME}}]


def scan(cands, deadline):
    """One eth_call: the USDC gain of every candidate against the same state; 0 = it would revert."""
    frm, ex, ov = ctx()
    res = rpc('eth_call', [{'from': frm, 'to': ex, 'data': scan_data(cands, deadline), 'gas': hex(120_000_000)}, 'latest'] + ov)
    h = res[2:]
    n = int(h[64:128], 16)
    if n != len(cands):
        raise RuntimeError('scan returned a wrong length')
    return [int(h[128 + 64 * i:192 + 64 * i], 16) for i in range(n)]


def eth_usd(fresh=False):
    """USDC per WETH from the Uniswap V3 WETH/USDC pool (token0 WETH 18 dp, token1 USDC 6 dp)."""
    if fresh or time.time() - _price['ts'] > PRICE_TTL_S:
        sq = int(rpc('eth_call', [{'to': P_IN, 'data': SEL_SLOT0}, 'latest'])[2:66], 16)
        _price['usd'] = (sq / 2**96) ** 2 * 1e12
        _price['ts'] = time.time()
    return _price['usd']


def winner_block(asset, send_block, me):
    """Nearest block around our send where someone else redeemed this asset at the vault."""
    logs = rpc('eth_getLogs', [{'address': VAULT, 'fromBlock': hex(max(0, send_block - 300)),
                               'toBlock': hex(send_block + 25), 'topics': [T_REDEEMED, None, '0x' + aw(asset)]}])
    best = None
    for x in logs:
        if '0x' + x['topics'][1][-40:].lower() == me.lower():
            continue
        b = int(x['blockNumber'], 16)
        if best is None or abs(b - send_block) < abs(best - send_block):
            best = b
    return best


def send_live(route, amount, data, gas_limit, max_fee, priority, gain):
    reply = signer().send(CHAIN, EXEC, data, 0, gas_limit, max_fee, max_priority_fee_per_gas=priority)
    h = reply.get('txHash') if isinstance(reply, dict) else None
    if not h:
        log('signer_reject', reply=reply)       # final: no retry
        return
    receipt = None
    for _ in range(20):
        time.sleep(1.0)
        receipt = rpc('eth_getTransactionReceipt', [h])
        if receipt:
            break
    if not receipt:
        log('send_result', hash=h, result='unknown', gas_used=None, winner_block=None, size_usdc=amount / 1e6, route=route)
        return
    b = int(receipt['blockNumber'], 16)
    used = int(receipt['gasUsed'], 16)
    status = int(receipt['status'], 16)
    try:
        other = winner_block(ROUTES[route][0], b, EXEC)
    except Exception:
        other = None
    log('send_result', hash=h, result='won' if status else 'lost', gas_used=used,
        gas_cost_wei=used * int(receipt['effectiveGasPrice'], 16) + int(receipt.get('l1Fee', '0x0'), 16), send_block=b,
        winner_block=other, blocks_after_winner=(b - other if other is not None else None),
        simulated_gain_usdc=gain / 1e6, size_usdc=amount / 1e6, route=route)


def evaluate(route, amount, gain):
    """Refine the size of the best route; send (live) or log (paper) only if its gross exceeds this send's gas cap."""
    frm, ex, ov = ctx()
    deadline = int(time.time()) + 60
    sizes = sorted({min(int(SIZE_MAX * 1e6), int(amount * f)) for f in REFINE})
    gains = scan([(route, a) for a in sizes], deadline)
    k = max(range(len(sizes)), key=lambda i: gains[i])
    if gains[k] > gain:
        amount, gain = sizes[k], gains[k]
    px = eth_usd(fresh=True)
    gain_wei = int(gain / 1e6 / px * 1e18)
    price = px * ETH_MARGIN
    base_fee = int(rpc('eth_gasPrice', []), 16)
    l1_fee = int(rpc('eth_call', [{'to': GAS_ORACLE, 'data': SEL_L1UB + word(TX_BYTES)}, 'latest']), 16)
    try:
        est = int(rpc('eth_estimateGas', [{'from': frm, 'to': ex, 'data': run_data(route, amount, 1, deadline)}, 'latest'] + ov), 16)
    except ReadBudgetExceeded:
        raise
    except Exception as e:
        if MODE == 'live':
            log('opportunity_skip', route=route, size_usdc=amount / 1e6, gain_usdc=gain / 1e6, reason='estimate_failed', error=str(e)[:160])
            return False
        est = int(GAS_LIMIT_FALLBACK / GAS_MARGIN)
    gas_limit = min(GAS_LIMIT_MAX, int(est * GAS_MARGIN))
    fee_ceiling = int((SEND_CAP_USD / price * 1e18 - l1_fee) / gas_limit)   # maxFeePerGas at which this send's cap is 0.95 USD
    priority = int(gain_wei * BID_SHARE / gas_limit)
    max_fee = min(fee_ceiling, int(base_fee * 1.3) + priority)
    priority = max(0, min(priority, max_fee))
    cap_wei = gas_limit * max_fee + l1_fee                           # the most this send can cost, in native
    gas_cap_usd = cap_wei / 1e18 * price
    reason = None
    if max_fee < base_fee:
        reason = 'base_fee_above_fee_cap'
    elif gas_cap_usd > SEND_CAP_USD:
        reason = 'gas_cap_over_usd_limit'
    elif gain / 1e6 < gas_cap_usd * GAIN_OVER_CAP:
        reason = 'gross_under_1.2x_gas_cap'
    if reason:
        log('opportunity_skip', route=route, size_usdc=amount / 1e6, gain_usdc=gain / 1e6, gas_cap_usd=gas_cap_usd,
            gas_limit=gas_limit, base_fee=base_fee, eth_usd=px, reason=reason)
        return False
    # the tx reverts unless the USDC gain covers its own gas cap (at the margined ETH price, rounded up)
    min_profit = int(gas_cap_usd * 1e6) + 1
    data = run_data(route, amount, min_profit, deadline)
    try:
        res = rpc('eth_call', [{'from': frm, 'to': ex, 'data': data, 'gas': hex(gas_limit)}, 'latest'] + ov)   # the exact bytes
        gain = int(res[2:66], 16)
    except ReadBudgetExceeded:
        raise
    except Exception as e:
        log('simulate_revert', route=route, size_usdc=amount / 1e6, error=str(e)[:200])
        return False
    log('opportunity', route=route, asset=ROUTES[route][0], pool=ROUTES[route][1], size_usdc=amount / 1e6, gain_usdc=gain / 1e6,
        min_profit_usdc=min_profit / 1e6, gas_cap_usd=gas_cap_usd, gas_limit=gas_limit, max_fee=max_fee, priority=priority,
        base_fee=base_fee, l1_fee_bound_wei=l1_fee, eth_usd=px, mode=MODE)
    if MODE == 'live':
        send_live(route, amount, data, gas_limit, max_fee, priority, gain)
    else:
        log('paper_sim', result='success', route=route, size_usdc=amount / 1e6, gain_usdc=gain / 1e6, gas_cap_usd=gas_cap_usd)
    return True


def main():
    log('start', mode=MODE, executor=EXEC if MODE == 'live' else PAPER_EXEC, poll_s=POLL_S, vault=VAULT,
        routes={r: v[1] for r, v in ROUTES.items()}, candidates=len(CANDS), cu_cap=CU_CAP)
    n = 0
    while True:
        try:
            profits = scan(CANDS, int(time.time()) + 60)
            n += 1
            now = time.time()
            live = [(p, r, a) for (r, a), p in zip(CANDS, profits) if _skip.get(r, 0) <= now]
            best, route, amount = max(live) if live else (0, None, 0)
            if n % 40 == 1:                                   # heartbeat about every 18 min
                log('poll', n=n, best_usdc=max(profits) / 1e6, open_routes=sorted({r for (r, _), p in zip(CANDS, profits) if p}))
            if best >= MIN_GAIN_USDC:
                sent = evaluate(route, amount, best)
                _skip[route] = time.time() + (SKIP_S if (not sent or MODE != 'live') else 0)
                if sent:
                    time.sleep(COOLDOWN_S)
                    continue
            time.sleep(POLL_S)
        except ReadBudgetExceeded as e:
            log('read_budget', error=str(e))
            now = datetime.datetime.now(datetime.timezone.utc)
            nxt = (now + datetime.timedelta(days=1)).replace(hour=0, minute=0, second=5, microsecond=0)
            time.sleep(max(60, (nxt - now).total_seconds()))
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
            log('relay_error', error=str(e)[:180])
            time.sleep(POLL_S)
        except Exception as e:
            log('loop_error', error=str(e)[:250])
            time.sleep(POLL_S)


if __name__ == '__main__':
    main()
