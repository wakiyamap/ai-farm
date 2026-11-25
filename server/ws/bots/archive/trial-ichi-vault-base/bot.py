#!/usr/bin/env python3
"""Trial: ICHI vaults on Base (Hydrex and Trebleswap pools), deposit / withdraw pricing versus another pool.

Each vault holds two tokens in its own concentrated-liquidity pool and takes single-sided deposits of one of them.
deposit() mints shares at the vault's own pool price (spot / TWAP), withdraw() pays the pro-rata two tokens. When
the vault's other token is dearer on another pool than the vault prices it, one transaction through the
IchiVaultArb3 executor flash-borrows the deposit token from Morpho Blue, deposits it, withdraws the shares at
once, closes on a PancakeSwap V3 (or Slipstream-style) pool, repays, and pays the gain to the bot wallet as native
ETH (WETH unwrapped) or USDC. Two closing modes: exact-in (sell all of the other token for the deposit token) and
exact-out (buy only the shortfall of the deposit token; the rest of the other token is the gain). The executor
reverts unless the gain is at least minProfit, so a lost attempt costs gas only.

The gap has no event worth a feed filter (it opens on swaps of busy WETH / USDC / cbBTC pools), so the bot polls
on a timer: one eth_call of the executor's scan() (every size of every route in one call) every POLL_S seconds.
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

# Route targets: all are call arguments of the executor (traces in scratch/ichi-f22b, proof in scratch/trial-ichi-vault-base)
MORPHO = '0xbbbbbbbbbb9cc5e90e3b3af64bdaf62c37eeffcb'   # Morpho Blue on Base (flash lender, no fee)
WETH = '0x4200000000000000000000000000000000000006'     # 18 decimals
USDC = '0x833589fcd6edb6e08f4c7c32d4f71b54bda02913'     # 6 decimals
CBBTC = '0xcbb7c0000ab88b473b1f5afd9ef808440eed33bf'    # 8 decimals
DEC = {WETH: 18, USDC: 6, CBBTC: 8}
P_WU = '0x72ab388e2e2f6facef59e3c3fa2c4e29011c2d38'     # PancakeSwap V3 WETH/USDC (token0 WETH)
P_WB = '0xc211e1f853a898bd1302385ccde55f33a8c4b3f3'     # PancakeSwap V3 WETH/cbBTC (token0 WETH)
P_WB2 = '0x7c7420dd105e2779316423ba3e973f434315efa9'    # Slipstream-style WETH/cbBTC (token0 WETH), uniswapV3SwapCallback
P_UB = '0xb94b22332abf5f89877a14cc88f2abc48c34b3df'     # PancakeSwap V3 USDC/cbBTC (token0 USDC)
SZ = {WETH: [30, 300, 1200, 3700], USDC: [50000, 500000, 2000000, 8000000], CBBTC: [0.1, 0.5, 0.9875]}
# name -> (vault, deposit token, closing pool, zeroForOne, exactOut, profit token). A size the vault refuses scans 0.
ROUTES = {
    'HYDX-3-cbBTC-WETH': ('0x558684fdad1d3b69f920b0c8e5ae9ff797e3f045', CBBTC, P_WB, True, True, WETH),
    'HYDX-3-cbBTC-WETH/slip': ('0x558684fdad1d3b69f920b0c8e5ae9ff797e3f045', CBBTC, P_WB2, True, True, WETH),
    'HYDX-0-WETH-USDC': ('0x07e72e46c319a6d5aca28ad52f5c41a7821989ad', WETH, P_WU, False, False, WETH),
    'HYDX-1-USDC-WETH': ('0x0c9be6df4e114d5cb04cbb934172be1fcc5526c6', USDC, P_WU, True, True, WETH),
    'TREB-1-USDC-WETH': ('0xa0cabee4d9f5beb83aaca2e030436d3c514d4fb4', USDC, P_WU, True, True, WETH),
    'HYDX-2-WETH-cbBTC': ('0xcf27dd90878dd88fd58bfffcbdfbc7e0cf7cd779', WETH, P_WB, False, False, WETH),
    'HYDX-2-WETH-cbBTC/slip': ('0xcf27dd90878dd88fd58bfffcbdfbc7e0cf7cd779', WETH, P_WB2, False, False, WETH),
    'HYDX-4-USDC-cbBTC': ('0x5febc3c9c1ce9f8e506963c498cda2cf92eedd27', USDC, P_UB, False, False, USDC),
    'HYDX-5-cbBTC-USDC': ('0x25154c35b24af82196bac0d143dd973335201b6a', CBBTC, P_UB, True, True, USDC),
    'TREB-0-WETH-USDC': ('0x669505c9126b5ac9f7ca2bf701f6221bab92d244', WETH, P_WU, False, False, WETH),
}
GAS_ORACLE = '0x420000000000000000000000000000000000000f'   # OP Stack GasPriceOracle predeploy
SEL_RUN = '0x18dd9bd6'     # cast sig run((address,address,uint256,address,address,bool,bool,address,uint256,uint256,bool))
SEL_SCAN = '0xd09d93c0'    # cast sig scan((address,address,uint256,address,address,bool,bool,address,uint256,uint256,bool)[])
SEL_SLOT0 = '0x3850c7bd'   # cast sig slot0()
SEL_L1UB = '0xf1c7a58b'    # cast sig getL1FeeUpperBound(uint256)
T_TRANSFER = '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'   # Transfer(address,address,uint256)
ZERO_TOPIC = '0x' + '0' * 64

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
GAS_LIMIT_MAX = 2_500_000
GAS_LIMIT_FALLBACK = 1_250_000  # used only if eth_estimateGas fails (paper); live never sends without an estimate
GAS_MARGIN = 1.25              # a take uses about 760-800k gas, a late revert about 910-960k
SEND_CAP_USD = 0.95            # gas limit x maxFeePerGas + L1 fee bound, at the pool ETH price x 1.15, stays under this
ETH_MARGIN = 1.15
BID_SHARE = 0.35               # priority fee bid is at most 35% of simulated gross
GAIN_OVER_CAP = 1.2            # send only if the simulated gain is at least 1.2 x this send's gas cap
MIN_GAIN_WEI = 2 * 10**13      # 0.00002 ETH (about 0.03 USD): smaller scan gains are not evaluated at all
TX_BYTES = 500                 # run() calldata is 356 bytes; the signed tx stays under 500
POLL_S = 27                    # one scan eth_call per poll: 3,200 polls/day x 26 CU = 83,200 CU
PRICE_TTL_S = 900
COOLDOWN_S = 5                 # after a send, before the next poll
CU_COST = {'eth_call': 26, 'eth_getLogs': 75, 'eth_getTransactionReceipt': 20, 'eth_blockNumber': 10,
           'eth_gasPrice': 10, 'eth_estimateGas': 26}
CU_CAP = 98_000                # relay CU/day, hard cap in code (trial rule: <= 100,000)
_id = 0
_price = {'ts': 0.0, 'usd': 0.0}


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
    """Params = (morpho, token, amount, vault, pool, zeroForOne, exactOut, profitToken, minProfit, deadline, unwrap):
    a static tuple of 11 words."""
    vault, token, pool, zfo, exact_out, ptok = ROUTES[route]
    return (aw(MORPHO) + aw(token) + word(amount) + aw(vault) + aw(pool) + word(1 if zfo else 0)
            + word(1 if exact_out else 0) + aw(ptok) + word(min_profit) + word(deadline)
            + word(1 if ptok == WETH else 0))             # WETH gain is unwrapped and paid as native ETH


def run_data(route, amount, min_profit, deadline):
    return SEL_RUN + enc_params(route, amount, min_profit, deadline)


def scan_data(cands, deadline):
    return SEL_SCAN + word(32) + word(len(cands)) + ''.join(enc_params(r, a, 0, deadline) for r, a in cands)


def units(route, size):
    return int(round(size * 10 ** DEC[ROUTES[route][1]]))


# candidates: every size on every route, one scan call
CANDS = [(r, s) for r, v in ROUTES.items() for s in SZ[v[1]]]


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


def scan(deadline):
    """One eth_call: the gain (profit-token units) of every candidate against the same state; 0 = it would revert."""
    frm, ex, ov = ctx()
    data = scan_data([(r, units(r, s)) for r, s in CANDS], deadline)
    res = rpc('eth_call', [{'from': frm, 'to': ex, 'data': data, 'gas': hex(120_000_000)}, 'latest'] + ov)
    h = res[2:]
    n = int(h[64:128], 16)
    if n != len(CANDS):
        raise RuntimeError('scan returned a wrong length')
    return [int(h[128 + 64 * i:192 + 64 * i], 16) for i in range(n)]


def eth_usd(fresh=False):
    """USDC per WETH from the PancakeSwap V3 WETH/USDC pool (token0 WETH 18 dp, token1 USDC 6 dp)."""
    if fresh or time.time() - _price['ts'] > PRICE_TTL_S:
        sq = int(rpc('eth_call', [{'to': P_WU, 'data': SEL_SLOT0}, 'latest'])[2:66], 16)
        _price['usd'] = (sq / 2**96) ** 2 * 1e12
        _price['ts'] = time.time()
    return _price['usd']


def to_wei(route, gain, px):
    """A gain in profit-token units as wei of ETH (USDC gains converted at the pool price)."""
    return gain if ROUTES[route][5] == WETH else int(gain / 1e6 / px * 1e18)


def winner_block(vault, send_block, exec_addr):
    """Nearest block around our send where someone else minted shares of the vault (a competing round trip)."""
    logs = rpc('eth_getLogs', [{'address': vault, 'fromBlock': hex(max(0, send_block - 300)),
                               'toBlock': hex(send_block + 25), 'topics': [T_TRANSFER, ZERO_TOPIC]}])
    best = None
    for x in logs:
        if '0x' + x['topics'][2][-40:].lower() == exec_addr.lower():
            continue
        b = int(x['blockNumber'], 16)
        if best is None or abs(b - send_block) < abs(best - send_block):
            best = b
    return best


def send_live(route, size, data, gas_limit, max_fee, priority, gain_wei):
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
        log('send_result', hash=h, result='unknown', gas_used=None, winner_block=None, size=size, route=route)
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
        simulated_gain_eth=gain_wei / 1e18, size=size, route=route)


def evaluate(profits, px):
    """Take the best candidate; send (live) or log (paper) only if its gross exceeds this send's gas cap."""
    i = max(range(len(profits)), key=lambda k: to_wei(CANDS[k][0], profits[k], px))
    if profits[i] == 0:
        return False
    route, size = CANDS[i]
    ptok = ROUTES[route][5]
    amount = units(route, size)
    frm, ex, ov = ctx()
    deadline = int(time.time()) + 60
    px = eth_usd(fresh=True)
    gain_wei = to_wei(route, profits[i], px)
    price = px * ETH_MARGIN
    base_fee = int(rpc('eth_gasPrice', []), 16)
    l1_fee = int(rpc('eth_call', [{'to': GAS_ORACLE, 'data': SEL_L1UB + word(TX_BYTES)}, 'latest']), 16)
    try:
        est = int(rpc('eth_estimateGas', [{'from': frm, 'to': ex, 'data': run_data(route, amount, 1, deadline)}, 'latest'] + ov), 16)
    except ReadBudgetExceeded:
        raise
    except Exception as e:
        if MODE == 'live':
            log('opportunity_skip', route=route, size=size, gain_eth=gain_wei / 1e18, reason='estimate_failed', error=str(e)[:160])
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
    elif gain_wei < cap_wei * GAIN_OVER_CAP:
        reason = 'gross_under_1.2x_gas_cap'
    if reason:
        log('opportunity_skip', route=route, size=size, gain_eth=gain_wei / 1e18, gas_cap_eth=cap_wei / 1e18,
            gas_cap_usd=gas_cap_usd, gas_limit=gas_limit, base_fee=base_fee, eth_usd=px, reason=reason)
        return False
    # the tx reverts unless the gain covers its own gas cap: in wei for a native payout, in USDC units (at the
    # margined ETH price, rounded up) for a USDC payout
    min_profit = cap_wei + 1 if ptok == WETH else int(gas_cap_usd * 1e6) + 1
    data = run_data(route, amount, min_profit, deadline)
    try:
        res = rpc('eth_call', [{'from': frm, 'to': ex, 'data': data, 'gas': hex(gas_limit)}, 'latest'] + ov)   # the exact bytes
        gain = int(res[2:66], 16)
    except ReadBudgetExceeded:
        raise
    except Exception as e:
        log('simulate_revert', route=route, size=size, error=str(e)[:200])
        return False
    gain_wei = to_wei(route, gain, px)
    log('opportunity', route=route, size=size, profit_token='ETH' if ptok == WETH else 'USDC', gain_raw=gain,
        gain_eth=gain_wei / 1e18, gain_usd=gain_wei / 1e18 * px, min_profit_raw=min_profit, gas_cap_usd=gas_cap_usd,
        gas_limit=gas_limit, max_fee=max_fee, priority=priority, base_fee=base_fee, l1_fee_bound_wei=l1_fee, eth_usd=px,
        mode=MODE, profits={f'{r}@{s}': p for (r, s), p in zip(CANDS, profits) if p})
    if MODE == 'live':
        send_live(route, size, data, gas_limit, max_fee, priority, gain_wei)
    else:
        log('paper_sim', result='success', route=route, size=size, gain_eth=gain_wei / 1e18, gas_cap_usd=gas_cap_usd)
    return True


def main():
    log('start', mode=MODE, executor=EXEC if MODE == 'live' else PAPER_EXEC, poll_s=POLL_S,
        routes={r: v[0] for r, v in ROUTES.items()}, candidates=len(CANDS), cu_cap=CU_CAP)
    n = 0
    while True:
        try:
            px = eth_usd()
            profits = scan(int(time.time()) + 60)
            n += 1
            best = max(to_wei(r, p, px) for (r, _), p in zip(CANDS, profits))
            if n % 40 == 1:                                   # heartbeat about every 18 min
                log('poll', n=n, best_eth=best / 1e18, eth_usd=px)
            if best >= MIN_GAIN_WEI and evaluate(profits, px):
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
