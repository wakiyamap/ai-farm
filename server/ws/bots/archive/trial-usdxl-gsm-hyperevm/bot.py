#!/usr/bin/env python3
"""Trial: USDXL redemption at HypurrFi's GSM versus the USDT0/USDXL pools on HyperEVM.

USDXL is HypurrFi's GHO-fork stablecoin. Its GSM has a public buyAsset(minAmount, receiver): burn USDXL, receive
USDT0 at 1:1 less a 1 pct fee (1.01 USDXL per USDT0). When a UniV3-style USDT0/USDXL pool gives more than 1.01 USDXL
per USDT0 after its own fee, one transaction through the UsdxlGsmArb executor buys USDXL on the pool, redeems it at
the GSM inside the pool's swap callback, pays the pool with that USDT0, sells the USDT0 that is left for WHYPE on the
WHYPE/USDT0 pool, unwraps it and pays it to the bot wallet as native HYPE. The executor reverts unless the native
paid out is at least minProfit, so a lost attempt costs gas only. No flash loan and no principal.

A gap opens when someone sells USDXL into one of five thin pools; none of them is worth a feed filter each, and the
gaps stand for tens of seconds (the incumbent takes them only once they clear its gas), so the bot polls on a timer:
one eth_call of the executor's scan() (all sizes on all pools in one call) every POLL_S seconds.
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

# Route targets: all are call arguments of the executor (HypurrFi docs / verified GsmWithHyFiPool; pools from USDXL transfers)
GSM = '0xcb17105f6a7a75d1f1c91317a4621d9aaafe96fd'          # USDXL GSM (USDT0), public buyAsset(uint256,address)
EXIT_POOL = '0xbd19e19e4b70eb7f248695a42208bc1edbbfb57d'    # WHYPE/USDT0 0.05%, token0 WHYPE: sell USDT0 = oneForZero
# USDT0/USDXL pools, token0 USDT0 in all five: buy USDXL = zeroForOne
POOLS = {
    'p200': '0xb814a0d1b15ccebdebbf4a6b74bd8ec7ea866262',   # fee 0.02 pct (the incumbent's main pool)
    'p500a': '0xb8c413ebf3985fd92e5cc416422e805cfd8b8165',  # fee 0.05 pct
    'p500b': '0xbed33b68de07557eb2af7b716478929df83e246a',  # fee 0.05 pct
    'p100': '0xea1694eb5ce437fa6f4e974cba12e80bfe3258a7',   # fee 0.01 pct
    'p3000': '0x4bd892af63015e7c56c1381c220c642d65d0f0b6',  # fee 0.3 pct
}
SIZES = [5, 10, 25, 50, 100]                                 # USDT0 spent on the pool (incumbent: 10 / 25 / 50)
SEL_RUN = '0xc8f90a1a'     # cast sig run((address,address,bool,uint256,address,bool,uint256,uint256))
SEL_SCAN = '0x2b0cbb00'    # cast sig scan((address,address,bool,uint256,address,bool,uint256,uint256)[])
SEL_SLOT0 = '0x3850c7bd'   # cast sig slot0()
T_BUYASSET = '0x35b18eb91d0f8ce2968fdf81c1ed9ac429776c7260cdb8bf35c314564e714f66'   # BuyAsset(address,address,uint256,uint256,uint256)

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
GAS_LIMIT_MAX = 1_500_000      # chain cap 2,000,000; a take uses about 520k, a late revert about 510-640k
GAS_LIMIT_FALLBACK = 700_000   # used only if eth_estimateGas fails (paper); live never sends without an estimate
GAS_MARGIN = 1.2
SEND_CAP_USD = 0.95            # gas limit x maxFeePerGas, valued at the pool HYPE price x 1.15, stays under this
HYPE_MARGIN = 1.15
BID_SHARE = 0.20               # priority fee bid is at most 20% of simulated gross
GAIN_OVER_CAP = 1.1            # send only if the simulated gain is at least 1.1 x this send's gas cap
MIN_GAIN_WEI = 4 * 10**13      # 0.00004 HYPE (about 0.0025 USD): smaller scan gains are not evaluated at all
POLL_S = 30                    # one scan eth_call per poll: 2,880 polls/day x 26 CU = 74,880 CU
COOLDOWN_S = 5                 # after a send, before the next poll
SKIP_REPEAT_S = 300            # the same standing gap that fails the gas test is re-evaluated at most every 5 min
CU_COST = {'eth_call': 26, 'eth_getLogs': 75, 'eth_getTransactionReceipt': 20, 'eth_blockNumber': 10,
           'eth_gasPrice': 10, 'eth_estimateGas': 26}
CU_CAP = 96_000                # relay CU/day, hard cap in code (trial rule: <= 100,000)
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


def enc_params(pool, amount, min_profit, deadline):
    """Params = (gsm, pool, zeroForOne, amountIn, exitPool, exitZeroForOne, minProfit, deadline): 8 static words."""
    return aw(GSM) + aw(pool) + word(1) + word(amount) + aw(EXIT_POOL) + word(0) + word(min_profit) + word(deadline)


def run_data(pool, amount, min_profit, deadline):
    return SEL_RUN + enc_params(pool, amount, min_profit, deadline)


def scan_data(cands, deadline):
    return SEL_SCAN + word(32) + word(len(cands)) + ''.join(enc_params(p, a, 0, deadline) for p, a in cands)


# candidates: every size on every pool, one scan call
CANDS = [(n, s) for n in POOLS for s in SIZES]


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
    """One eth_call: the native gain (wei) of every candidate against the same state; 0 = it would revert."""
    frm, ex, ov = ctx()
    data = scan_data([(POOLS[n], s * 10**6) for n, s in CANDS], deadline)
    res = rpc('eth_call', [{'from': frm, 'to': ex, 'data': data, 'gas': hex(50_000_000)}, 'latest'] + ov)
    h = res[2:]
    n = int(h[64:128], 16)
    if n != len(CANDS):
        raise RuntimeError('scan returned a wrong length')
    return [int(h[128 + 64 * i:192 + 64 * i], 16) for i in range(n)]


def hype_usd():
    sq = int(rpc('eth_call', [{'to': EXIT_POOL, 'data': SEL_SLOT0}, 'latest'])[2:66], 16)
    return (sq / 2**96) ** 2 * 1e12        # USDT0 (6 dp) per WHYPE (18 dp)


def winner_block(send_block, exec_addr):
    """Nearest block around our send where someone else redeemed at the GSM (BuyAsset by another originator)."""
    logs = rpc('eth_getLogs', [{'address': GSM, 'fromBlock': hex(max(0, send_block - 120)),
                               'toBlock': hex(send_block + 5), 'topics': [T_BUYASSET]}])
    best = None
    for x in logs:
        if '0x' + x['topics'][1][-40:].lower() == exec_addr.lower():
            continue
        b = int(x['blockNumber'], 16)
        if best is None or abs(b - send_block) < abs(best - send_block):
            best = b
    return best


def send_live(pool, size, data, gas_limit, max_fee, priority, gain):
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
        log('send_result', hash=h, result='unknown', gas_used=None, winner_block=None, size_usdt0=size, pool=pool)
        return
    b = int(receipt['blockNumber'], 16)
    used = int(receipt['gasUsed'], 16)
    status = int(receipt['status'], 16)
    try:
        other = winner_block(b, EXEC)
    except Exception:
        other = None
    log('send_result', hash=h, result='won' if status else 'lost', gas_used=used,
        gas_cost_wei=used * int(receipt['effectiveGasPrice'], 16), send_block=b, winner_block=other,
        blocks_after_winner=(b - other if other is not None else None), simulated_gain_hype=gain / 1e18,
        size_usdt0=size, pool=pool)


_last_skip = {}


def evaluate(profits):
    """Take the best candidate; send (live) or log (paper) only if its gross exceeds this send's gas cap."""
    i = max(range(len(profits)), key=lambda k: profits[k])
    gain = profits[i]
    if gain == 0:
        return False
    name, size = CANDS[i]
    key = (name, size, gain)
    if time.time() - _last_skip.get(key, 0) < SKIP_REPEAT_S:      # the same standing gap already failed the gas test
        return False
    pool = POOLS[name]
    amount = size * 10**6
    frm, ex, ov = ctx()
    deadline = int(time.time()) + 60
    base_fee = int(rpc('eth_gasPrice', []), 16)
    price = hype_usd() * HYPE_MARGIN
    try:
        est = int(rpc('eth_estimateGas', [{'from': frm, 'to': ex, 'data': run_data(pool, amount, 1, deadline)}, 'latest'] + ov), 16)
    except ReadBudgetExceeded:
        raise
    except Exception as e:
        if MODE == 'live':
            log('opportunity_skip', pool=name, size_usdt0=size, gain_hype=gain / 1e18, reason='estimate_failed', error=str(e)[:160])
            _last_skip[key] = time.time()
            return False
        est = int(GAS_LIMIT_FALLBACK / GAS_MARGIN)
    gas_limit = min(GAS_LIMIT_MAX, int(est * GAS_MARGIN))
    fee_ceiling = int(SEND_CAP_USD / price * 1e18 / gas_limit)       # maxFeePerGas at which this send's cap is 0.95 USD
    priority = int(gain * BID_SHARE / gas_limit)
    max_fee = min(fee_ceiling, int(base_fee * 1.15) + priority)
    priority = min(priority, max_fee)
    cap_wei = gas_limit * max_fee                                    # the most this send can cost, in native
    gas_cap_usd = cap_wei / 1e18 * price
    reason = None
    if max_fee < base_fee:
        reason = 'base_fee_above_fee_cap'
    elif gas_cap_usd > SEND_CAP_USD:
        reason = 'gas_cap_over_usd_limit'
    elif gain < cap_wei * GAIN_OVER_CAP:
        reason = 'gross_under_1.1x_gas_cap'
    if reason:
        log('opportunity_skip', pool=name, size_usdt0=size, gain_hype=gain / 1e18, gas_cap_hype=cap_wei / 1e18,
            gas_cap_usd=gas_cap_usd, gas_limit=gas_limit, base_fee=base_fee, hype_usd=price, reason=reason)
        _last_skip[key] = time.time()
        if len(_last_skip) > 200:
            _last_skip.clear()
        return False
    min_profit = cap_wei + 1                 # the tx reverts unless the native gain covers its own gas cap
    data = run_data(pool, amount, min_profit, deadline)
    try:
        res = rpc('eth_call', [{'from': frm, 'to': ex, 'data': data, 'gas': hex(gas_limit)}, 'latest'] + ov)   # the exact bytes
        gain = int(res[2:66], 16)
    except ReadBudgetExceeded:
        raise
    except Exception as e:
        log('simulate_revert', pool=name, size_usdt0=size, error=str(e)[:200])
        return False
    log('opportunity', pool=name, size_usdt0=size, gain_hype=gain / 1e18, gain_usd=gain / 1e18 * price / HYPE_MARGIN,
        min_profit_hype=min_profit / 1e18, gas_cap_usd=gas_cap_usd, gas_limit=gas_limit, max_fee=max_fee,
        priority=priority, base_fee=base_fee, hype_usd=price, mode=MODE,
        profits={f'{n}:{s}': p / 1e18 for (n, s), p in zip(CANDS, profits) if p})
    if MODE == 'live':
        send_live(name, size, data, gas_limit, max_fee, priority, gain)
    else:
        log('paper_sim', result='success', pool=name, size_usdt0=size, gain_hype=gain / 1e18, gas_cap_usd=gas_cap_usd)
        _last_skip[key] = time.time()        # paper: the gap stays (nothing is sent); do not log it every poll
    return True


def main():
    log('start', mode=MODE, executor=EXEC if MODE == 'live' else PAPER_EXEC, poll_s=POLL_S,
        pools=POOLS, sizes=SIZES, cu_cap=CU_CAP)
    n = 0
    while True:
        try:
            profits = scan(int(time.time()) + 60)
            n += 1
            if n % 40 == 1:                                   # heartbeat about every 20 min
                log('poll', n=n, best_hype=max(profits) / 1e18)
            if max(profits) >= MIN_GAIN_WEI and evaluate(profits):
                time.sleep(COOLDOWN_S if MODE == 'live' else POLL_S)
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
