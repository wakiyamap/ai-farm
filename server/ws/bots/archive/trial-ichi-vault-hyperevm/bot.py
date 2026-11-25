#!/usr/bin/env python3
"""Trial: ICHI vault IV-NEST-16 (USDC deposit) deposit / withdraw pricing versus the HyperCore-priced WHYPE/USDC pool.

The vault holds USDC + WHYPE in Nest's Algebra WHYPE/USDC pool. deposit() mints shares at that pool's own price
(spot / TWAP), withdraw() pays the pro-rata USDC + WHYPE. When the HyperCore HYPE price is above the Nest pool's
price, one transaction through the IchiVaultArb executor flash-borrows USDC from Morpho Blue, deposits it, withdraws
the shares at once, sells the WHYPE on pool 0x586304.. (which quotes from HyperCore), repays, and pays the USDC gain
to the bot wallet. The executor reverts unless the gain is at least minProfit, so a lost attempt costs gas only.

The price gap has no event of its own (HyperCore moves, the Nest pool lags), so the bot polls on a timer: one
eth_call of the executor's scan() (all sizes in one call) every POLL_S seconds.
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

# Route targets: all are call arguments of the executor (trace of 0xcd7b75eb.., scratch/trial-ichi-vault-hyperevm)
MORPHO = '0x68e37de8d93d3496ae143f2e900490f6280c57cd'      # Morpho Blue (flash lender, no fee)
USDC = '0xb88339cb7199b77e23db6e890353e22632ba630f'        # HyperEVM USDC, 6 decimals
VAULT = '0xb792f94ed56ed0ba163e5ba139e2bd0029a81d0a'       # ICHI vault IV-NEST-16-USDC-WHYPE (token0 WHYPE, token1 USDC)
SELL_POOL = '0x586304481f7be6cb7738bbb913a693dfdd801480'   # WHYPE/USDC pool priced from HyperCore; token0 WHYPE
SELL_ZERO_FOR_ONE = True                                    # WHYPE -> USDC
POOL_WHYPE = '0xbd19e19e4b70eb7f248695a42208bc1edbbfb57d'  # WHYPE/USDT0 0.05%, token0 WHYPE: HYPE price for the gas cap
SEL_RUN = '0x7f0baf1c'     # cast sig run((address,address,uint256,address,(address,bool)[],uint256,uint256))
SEL_SCAN = '0x9d46098b'    # cast sig scan((address,address,uint256,address,(address,bool)[],uint256,uint256)[])
SEL_SLOT0 = '0x3850c7bd'    # cast sig slot0()
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
GAS_LIMIT_FALLBACK = 1_100_000  # used only if eth_estimateGas fails (paper); live never sends without an estimate
GAS_MARGIN = 1.25              # a take uses about 735k gas, a late revert about 880k
SEND_CAP_USD = 0.95            # gas limit x maxFeePerGas, valued at the pool HYPE price x 1.15, stays under this
HYPE_MARGIN = 1.15
BID_SHARE = 0.35               # priority fee bid is at most 35% of simulated gross
GAIN_OVER_CAP = 1.2            # send only if the simulated gain is at least 1.2 x this send's gas cap
MIN_GAIN_UNITS = 30_000        # 0.03 USDC: smaller scan gains are not evaluated at all
SIZES = [20_000, 60_000, 180_000, 500_000, 1_200_000, 3_000_000]   # USDC flash sizes; the incumbents use 0.3M-3.2M
POLL_S = 27                    # one scan eth_call per poll: 3,200 polls/day x 26 CU = 83,200 CU
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


def enc_params(amount, min_profit, deadline):
    """Params = (morpho, token, amount, vault, Hop[] hops, minProfit, deadline); dynamic tuple, one hop."""
    head = aw(MORPHO) + aw(USDC) + word(amount) + aw(VAULT) + word(7 * 32) + word(min_profit) + word(deadline)
    tail = word(1) + aw(SELL_POOL) + word(1 if SELL_ZERO_FOR_ONE else 0)
    return head + tail


def run_data(amount, min_profit, deadline):
    return SEL_RUN + word(32) + enc_params(amount, min_profit, deadline)


def scan_data(amounts, deadline):
    encs = [enc_params(a, 0, deadline) for a in amounts]
    offs, pos = [], 32 * len(encs)
    for e in encs:
        offs.append(word(pos))
        pos += len(e) // 2
    return SEL_SCAN + word(32) + word(len(encs)) + ''.join(offs) + ''.join(encs)


AMOUNTS = [s * 10**6 for s in SIZES]


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
    """One eth_call: the USDC gain (6 dp) of every size against the same state; 0 = it would revert."""
    frm, ex, ov = ctx()
    res = rpc('eth_call', [{'from': frm, 'to': ex, 'data': scan_data(AMOUNTS, deadline), 'gas': hex(30_000_000)}, 'latest'] + ov)
    h = res[2:]
    n = int(h[64:128], 16)
    if n != len(AMOUNTS):
        raise RuntimeError('scan returned a wrong length')
    return [int(h[128 + 64 * i:192 + 64 * i], 16) for i in range(n)]


def hype_usd():
    sq = int(rpc('eth_call', [{'to': POOL_WHYPE, 'data': SEL_SLOT0}, 'latest'])[2:66], 16)
    return (sq / 2**96) ** 2 * 1e12        # USDT0 (6 dp) per WHYPE (18 dp)


def winner_block(send_block, exec_addr):
    """Nearest block around our send where someone else minted shares of the vault (a competing round trip)."""
    logs = rpc('eth_getLogs', [{'address': VAULT, 'fromBlock': hex(max(0, send_block - 120)),
                               'toBlock': hex(send_block + 5), 'topics': [T_TRANSFER, ZERO_TOPIC]}])
    best = None
    for x in logs:
        if '0x' + x['topics'][2][-40:].lower() == exec_addr.lower():
            continue
        b = int(x['blockNumber'], 16)
        if best is None or abs(b - send_block) < abs(best - send_block):
            best = b
    return best


def send_live(size, data, gas_limit, max_fee, priority, gain):
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
        log('send_result', hash=h, result='unknown', gas_used=None, winner_block=None, size_usdc=size)
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
        blocks_after_winner=(b - other if other is not None else None), simulated_gain_usdc=gain / 1e6,
        size_usdc=size)


def evaluate(profits):
    """Take the best size; send (live) or log (paper) only if its gross exceeds this send's gas cap."""
    i = max(range(len(profits)), key=lambda k: profits[k])
    gain = profits[i]
    if gain == 0:
        return False
    amount, size = AMOUNTS[i], SIZES[i]
    frm, ex, ov = ctx()
    deadline = int(time.time()) + 60
    base_fee = int(rpc('eth_gasPrice', []), 16)
    price = hype_usd() * HYPE_MARGIN
    try:
        est = int(rpc('eth_estimateGas', [{'from': frm, 'to': ex, 'data': run_data(amount, 1, deadline)}, 'latest'] + ov), 16)
    except ReadBudgetExceeded:
        raise
    except Exception as e:
        if MODE == 'live':
            log('opportunity_skip', size_usdc=size, gain_usdc=gain / 1e6, reason='estimate_failed', error=str(e)[:160])
            return False
        est = int(GAS_LIMIT_FALLBACK / GAS_MARGIN)
    gas_limit = min(GAS_LIMIT_MAX, int(est * GAS_MARGIN))
    gross_usd = gain / 1e6
    gain_wei = int(gross_usd / price * 1e18)
    fee_ceiling = int(SEND_CAP_USD / price * 1e18 / gas_limit)       # maxFeePerGas at which this send's cap is 0.95 USD
    priority = int(gain_wei * BID_SHARE / gas_limit)
    max_fee = min(fee_ceiling, int(base_fee * 1.3) + priority)
    priority = min(priority, max_fee)
    gas_cap_usd = gas_limit * max_fee / 1e18 * price
    reason = None
    if max_fee < base_fee:
        reason = 'base_fee_above_fee_cap'
    elif gas_cap_usd > SEND_CAP_USD:
        reason = 'gas_cap_over_usd_limit'
    elif gross_usd < gas_cap_usd * GAIN_OVER_CAP:
        reason = 'gross_under_1.2x_gas_cap'
    if reason:
        log('opportunity_skip', size_usdc=size, gain_usdc=gross_usd, gas_cap_usd=gas_cap_usd, gas_limit=gas_limit,
            base_fee=base_fee, hype_usd=price, reason=reason)
        return False
    min_profit = max(1, int(gas_cap_usd * 1e6) + 1)          # the tx reverts unless the gain covers its own gas cap
    data = run_data(amount, min_profit, deadline)
    try:
        res = rpc('eth_call', [{'from': frm, 'to': ex, 'data': data, 'gas': hex(gas_limit)}, 'latest'] + ov)   # the exact bytes
        gain = int(res[2:66], 16)
    except ReadBudgetExceeded:
        raise
    except Exception as e:
        log('simulate_revert', size_usdc=size, error=str(e)[:200])
        return False
    log('opportunity', size_usdc=size, gain_usdc=gain / 1e6, min_profit_usdc=min_profit / 1e6, gas_cap_usd=gas_cap_usd,
        gas_limit=gas_limit, max_fee=max_fee, priority=priority, base_fee=base_fee, hype_usd=price, mode=MODE,
        profits={str(s): p / 1e6 for s, p in zip(SIZES, profits) if p})
    if MODE == 'live':
        send_live(size, data, gas_limit, max_fee, priority, gain)
    else:
        log('paper_sim', result='success', size_usdc=size, gain_usdc=gain / 1e6, gas_cap_usd=gas_cap_usd)
    return True


def main():
    log('start', mode=MODE, executor=EXEC if MODE == 'live' else PAPER_EXEC, poll_s=POLL_S, sizes=SIZES,
        vault=VAULT, sell_pool=SELL_POOL, cu_cap=CU_CAP)
    n = 0
    while True:
        try:
            profits = scan(int(time.time()) + 60)
            n += 1
            if n % 40 == 1:                                   # heartbeat about every 18 min
                log('poll', n=n, best_usdc=max(profits) / 1e6)
            if max(profits) >= MIN_GAIN_UNITS and evaluate(profits):
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
