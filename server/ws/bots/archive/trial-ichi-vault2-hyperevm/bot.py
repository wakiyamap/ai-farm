#!/usr/bin/env python3
"""Trial: the two WHYPE-deposit ICHI vaults on Nest, deposit / withdraw pricing versus another pool.

IV-NEST-2 holds NEST + WHYPE in Nest's Algebra NEST/WHYPE pool; IV-NEST-17 holds WHYPE + USDC in Nest's Algebra
WHYPE/USDC pool. deposit() mints shares at the vault's own pool price (spot / TWAP), withdraw() pays the pro-rata
two tokens. When the other token (NEST, USDC) is dearer on another pool than on the vault's own pool, one
transaction through the IchiVaultArb2 executor flash-borrows WHYPE from Morpho Blue, deposits it, withdraws the
shares at once, sells the other token for WHYPE (IV-NEST-2: NEST -> kHYPE -> WHYPE, routes A / B; IV-NEST-17:
USDC -> WHYPE on a UniV3-style pool, route C), repays, unwraps the WHYPE gain and pays it to the bot wallet as
native HYPE. The executor reverts unless the gain is at least minProfit, so a lost attempt costs gas only.

The price gap has no event worth a feed filter (it opens on swaps of busy pools), so the bot polls on a timer:
one eth_call of the executor's scan() (all sizes of all routes in one call) every POLL_S seconds.
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
CHAIN = 'hyperevm'

# Route targets: all are call arguments of the executor (trace of 0x1a123c76.., scratch/trial-ichi-vault2-hyperevm)
MORPHO = '0x68e37de8d93d3496ae143f2e900490f6280c57cd'      # Morpho Blue (flash lender, no fee)
WHYPE = '0x5555555555555555555555555555555555555555'       # wrapped HYPE, 18 decimals
V2 = '0x6bd209f208d58f1db5497ec49d14bf9945f5b104'          # ICHI vault IV-NEST-2 (token0 NEST, token1 WHYPE)
V17 = '0x71b7da3a4f9a5964f34d997faa72eb7ac037e02f'         # ICHI vault IV-NEST-17 (token0 WHYPE, token1 USDC)
P_NEST_KHYPE = '0x23d95b24ad0c1ff48816a87e1e65dac4fa883afb'  # Algebra NEST/kHYPE, token0 NEST: sell NEST = zeroForOne
P_KHYPE_A = '0xbe352daf66af94ccf2012a154a67daef95facb91'   # UniV3-style WHYPE/kHYPE, token0 WHYPE: sell kHYPE = oneForZero
P_KHYPE_B = '0x705d5dda03d170384eb43eb1aa692a6fc548306f'   # UniV3-style WHYPE/kHYPE, token0 WHYPE
P_WHYPE_USDC = '0x6c9a33e3b592c0d65b3ba59355d5be0d38259285'  # UniV3-style WHYPE/USDC, token0 WHYPE: sell USDC = oneForZero
# route key -> (vault, sell hops, WHYPE flash sizes). A size the vault refuses scans 0.
ROUTES = {
    'A': (V2, [(P_NEST_KHYPE, True), (P_KHYPE_A, False)], [15, 40, 80, 120, 180, 260]),      # incumbents use about 100
    'B': (V2, [(P_NEST_KHYPE, True), (P_KHYPE_B, False)], [15, 40, 80, 120, 180, 260]),
    'C': (V17, [(P_WHYPE_USDC, False)], [300, 1000, 3000, 10000, 30000, 64000, 120000]),     # incumbents use about 63,600
}
POOL_WHYPE = '0xbd19e19e4b70eb7f248695a42208bc1edbbfb57d'  # WHYPE/USDT0 0.05%, token0 WHYPE: HYPE price for the gas cap
SEL_RUN = '0x72c7c749'     # cast sig run((address,address,uint256,address,(address,bool)[],uint256,uint256,bool))
SEL_SCAN = '0xe13bc686'    # cast sig scan((address,address,uint256,address,(address,bool)[],uint256,uint256,bool)[])
SEL_SLOT0 = '0x3850c7bd'   # cast sig slot0()
T_TRANSFER = '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'   # Transfer(address,address,uint256)
ZERO_TOPIC = '0x' + '0' * 64

PAPER_EXEC = '0x8f7a45ebde059392e46a46dcc14ab24681a961ea'    # fork deployment; paper code override only
PAPER_OWNER = '0x1111111111111111111111111111111111111111'   # the owner baked into that deployment (immutable)
EXEC = os.environ.get('EXECUTOR_ADDR_HYPEREVM') or os.environ.get('EXECUTOR_ADDR')
if MODE == 'live' and not EXEC:
    raise SystemExit('EXECUTOR_ADDR_HYPEREVM or EXECUTOR_ADDR is required in live mode')
RUNTIME = (HERE / 'executor-runtime.hex').read_text().strip()
if not RUNTIME.startswith('0x'):
    raise SystemExit('missing paper executor runtime')
LOG = HERE / 'logs' / 'bot.jsonl'
CU_FILE = HERE / 'state' / 'cu.json'
LOG.parent.mkdir(exist_ok=True)
CU_FILE.parent.mkdir(exist_ok=True)

# ---- loss guard (trial rule: every send's gas limit x maxFeePerGas < 1 USD) ----
GAS_LIMIT_MAX = 1_900_000      # chain cap 2,000,000
GAS_LIMIT_FALLBACK = 1_250_000  # used only if eth_estimateGas fails (paper); live never sends without an estimate
GAS_MARGIN = 1.25              # a take uses about 813k gas, a late revert about 970k
SEND_CAP_USD = 0.95            # gas limit x maxFeePerGas, valued at the pool HYPE price x 1.15, stays under this
HYPE_MARGIN = 1.15
BID_SHARE = 0.35               # priority fee bid is at most 35% of simulated gross
GAIN_OVER_CAP = 1.2            # send only if the simulated gain is at least 1.2 x this send's gas cap
MIN_GAIN_WEI = 5 * 10**14      # 0.0005 WHYPE (about 0.03 USD): smaller scan gains are not evaluated at all
POLL_S = 27                   # one scan eth_call per poll: 3,200 polls/day x 26 CU = 83,200 CU
COOLDOWN_S = 5                 # after a send, before the next poll
CU_COST = {'eth_call': 26, 'eth_getLogs': 75, 'eth_getTransactionReceipt': 20, 'eth_blockNumber': 10,
           'eth_gasPrice': 10, 'eth_estimateGas': 26}
CU_CAP = 98_000                # relay CU/day, hard cap in code (trial rule: <= 100,000)
_id = 0


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


def enc_params(vault, amount, hops, min_profit, deadline):
    """Params = (morpho, token, amount, vault, Hop[] hops, minProfit, deadline, unwrap); a dynamic tuple."""
    head = (aw(MORPHO) + aw(WHYPE) + word(amount) + aw(vault) + word(8 * 32) + word(min_profit) + word(deadline)
            + word(1))                                    # unwrap = true: the gain is paid as native HYPE
    tail = word(len(hops)) + ''.join(aw(p) + word(1 if z else 0) for p, z in hops)
    return head + tail


def run_data(vault, amount, hops, min_profit, deadline):
    return SEL_RUN + word(32) + enc_params(vault, amount, hops, min_profit, deadline)


def scan_data(cands, deadline):
    encs = [enc_params(v, a, h, 0, deadline) for v, a, h in cands]
    offs, pos = [], 32 * len(encs)
    for e in encs:
        offs.append(word(pos))
        pos += len(e) // 2
    return SEL_SCAN + word(32) + word(len(encs)) + ''.join(offs) + ''.join(encs)


# candidates: every size on every route, one scan call
CANDS = [(r, s) for r, (_, _, sizes) in ROUTES.items() for s in sizes]


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
    """One eth_call: the WHYPE gain (wei) of every candidate against the same state; 0 = it would revert."""
    frm, ex, ov = ctx()
    data = scan_data([(ROUTES[r][0], s * 10**18, ROUTES[r][1]) for r, s in CANDS], deadline)
    res = rpc('eth_call', [{'from': frm, 'to': ex, 'data': data, 'gas': hex(50_000_000)}, 'latest'] + ov)
    h = res[2:]
    n = int(h[64:128], 16)
    if n != len(CANDS):
        raise RuntimeError('scan returned a wrong length')
    return [int(h[128 + 64 * i:192 + 64 * i], 16) for i in range(n)]


def hype_usd():
    sq = int(rpc('eth_call', [{'to': POOL_WHYPE, 'data': SEL_SLOT0}, 'latest'])[2:66], 16)
    return (sq / 2**96) ** 2 * 1e12        # USDT0 (6 dp) per WHYPE (18 dp)


def winner_block(vault, send_block, exec_addr):
    """Nearest block around our send where someone else minted shares of the vault (a competing round trip)."""
    logs = rpc('eth_getLogs', [{'address': vault, 'fromBlock': hex(max(0, send_block - 120)),
                               'toBlock': hex(send_block + 5), 'topics': [T_TRANSFER, ZERO_TOPIC]}])
    best = None
    for x in logs:
        if '0x' + x['topics'][2][-40:].lower() == exec_addr.lower():
            continue
        b = int(x['blockNumber'], 16)
        if best is None or abs(b - send_block) < abs(best - send_block):
            best = b
    return best


def send_live(route, size, data, gas_limit, max_fee, priority, gain):
    reply = signer().send(CHAIN, EXEC, data, 0, gas_limit, max_fee, max_priority_fee_per_gas=priority)
    h = reply.get('txHash') if isinstance(reply, dict) else None
    if not h:
        log('signer_reject', reply=reply)       # final: no retry
        return
    receipt = None
    for _ in range(25):
        time.sleep(1.0)
        receipt = rpc('eth_getTransactionReceipt', [h])
        if receipt:
            break
    if not receipt:
        log('send_result', hash=h, result='unknown', gas_used=None, winner_block=None, size_whype=size, route=route)
        return
    b = int(receipt['blockNumber'], 16)
    used = int(receipt['gasUsed'], 16)
    status = int(receipt['status'], 16)
    try:
        other = winner_block(ROUTES[route][0], b, EXEC)
    except Exception:
        other = None
    log('send_result', hash=h, result='won' if status else 'lost', gas_used=used,
        gas_cost_wei=used * int(receipt['effectiveGasPrice'], 16), send_block=b, winner_block=other,
        blocks_after_winner=(b - other if other is not None else None), simulated_gain_hype=gain / 1e18,
        size_whype=size, route=route)


def evaluate(profits):
    """Take the best candidate; send (live) or log (paper) only if its gross exceeds this send's gas cap."""
    i = max(range(len(profits)), key=lambda k: profits[k])
    gain = profits[i]
    if gain == 0:
        return False
    route, size = CANDS[i]
    vault, hops, _ = ROUTES[route]
    amount = size * 10**18
    frm, ex, ov = ctx()
    deadline = int(time.time()) + 60
    base_fee = int(rpc('eth_gasPrice', []), 16)
    price = hype_usd() * HYPE_MARGIN
    try:
        est = int(rpc('eth_estimateGas', [{'from': frm, 'to': ex, 'data': run_data(vault, amount, hops, 1, deadline)}, 'latest'] + ov), 16)
    except ReadBudgetExceeded:
        raise
    except Exception as e:
        if MODE == 'live':
            log('opportunity_skip', route=route, size_whype=size, gain_hype=gain / 1e18, reason='estimate_failed', error=str(e)[:160])
            return False
        est = int(GAS_LIMIT_FALLBACK / GAS_MARGIN)
    gas_limit = min(GAS_LIMIT_MAX, int(est * GAS_MARGIN))
    fee_ceiling = int(SEND_CAP_USD / price * 1e18 / gas_limit)       # maxFeePerGas at which this send's cap is 0.95 USD
    priority = int(gain * BID_SHARE / gas_limit)
    max_fee = min(fee_ceiling, int(base_fee * 1.3) + priority)
    priority = min(priority, max_fee)
    cap_wei = gas_limit * max_fee                                    # the most this send can cost, in native
    gas_cap_usd = cap_wei / 1e18 * price
    reason = None
    if max_fee < base_fee:
        reason = 'base_fee_above_fee_cap'
    elif gas_cap_usd > SEND_CAP_USD:
        reason = 'gas_cap_over_usd_limit'
    elif gain < cap_wei * GAIN_OVER_CAP:
        reason = 'gross_under_1.2x_gas_cap'
    if reason:
        log('opportunity_skip', route=route, size_whype=size, gain_hype=gain / 1e18, gas_cap_hype=cap_wei / 1e18,
            gas_cap_usd=gas_cap_usd, gas_limit=gas_limit, base_fee=base_fee, hype_usd=price, reason=reason)
        return False
    min_profit = cap_wei + 1                 # the tx reverts unless the native gain covers its own gas cap
    data = run_data(vault, amount, hops, min_profit, deadline)
    try:
        res = rpc('eth_call', [{'from': frm, 'to': ex, 'data': data, 'gas': hex(gas_limit)}, 'latest'] + ov)   # the exact bytes
        gain = int(res[2:66], 16)
    except ReadBudgetExceeded:
        raise
    except Exception as e:
        log('simulate_revert', route=route, size_whype=size, error=str(e)[:200])
        return False
    log('opportunity', route=route, size_whype=size, gain_hype=gain / 1e18, gain_usd=gain / 1e18 * price / HYPE_MARGIN,
        min_profit_hype=min_profit / 1e18, gas_cap_usd=gas_cap_usd, gas_limit=gas_limit, max_fee=max_fee,
        priority=priority, base_fee=base_fee, hype_usd=price, mode=MODE,
        profits={f'{r}{s}': p / 1e18 for (r, s), p in zip(CANDS, profits) if p})
    if MODE == 'live':
        send_live(route, size, data, gas_limit, max_fee, priority, gain)
    else:
        log('paper_sim', result='success', route=route, size_whype=size, gain_hype=gain / 1e18, gas_cap_usd=gas_cap_usd)
    return True


def main():
    log('start', mode=MODE, executor=EXEC if MODE == 'live' else PAPER_EXEC, poll_s=POLL_S,
        routes={r: {'vault': v, 'sizes': s} for r, (v, _, s) in ROUTES.items()}, cu_cap=CU_CAP)
    n = 0
    while True:
        try:
            profits = scan(int(time.time()) + 60)
            n += 1
            if n % 40 == 1:                                   # heartbeat about every 18 min
                log('poll', n=n, best_hype=max(profits) / 1e18)
            if max(profits) >= MIN_GAIN_WEI and evaluate(profits):
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
