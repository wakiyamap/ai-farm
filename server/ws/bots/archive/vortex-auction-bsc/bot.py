#!/usr/bin/env python3
"""vortex-auction-bsc: buy the BNB lot of Bancor's CarbonVortex on BSC when its Dutch auction falls under the market.

The Vortex (0x5bCA3389...) sells the native BNB it holds for Binance-Peg ETH; the ask starts at the maximum at each
reset and halves every 12 h, so the time it crosses the market price is known days ahead. The bot reads the ask and
the PancakeSwap V3 ETH/WBNB price, sleeps toward the computed crossing time (never polling every block), and when the
ask is MIN_DISCOUNT_BPS under the pool price it simulates the executor call and sends it (BOT_MODE=live) or logs a
paper simulation (BOT_MODE=paper). The executor borrows the ETH by a flash swap, buys the lot, repays the pool in WBNB
and reverts unless the bot wallet gains at least minProfit BNB. One transaction, no principal.
"""
import datetime
import json
import math
import os
import sys
import time
from pathlib import Path
import urllib.request

sys.path.append('/opt/farm/lib')   # farmbot_signer lives here; the live service does not add it

HERE = Path(__file__).resolve().parent
MODE = os.environ.get('BOT_MODE', 'paper')
LANE = os.environ.get('RPC_LANE', 'paper')
RELAY = os.environ['RPC_RELAY_URL'].rstrip('/')
CHAIN = 'bsc'

VORTEX = '0x5bCA3389786385a35bca14C2D0582adC6cb2482e'   # bancorprotocol/carbon-contracts deployments/bsc/CarbonVortex.json
NATIVE = '0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE'   # the Vortex's targetToken() (native BNB)
ETH = '0x2170Ed0880ac9A755fd29B2688956BD959F933F8'      # the Vortex's finalTargetToken() (Binance-Peg ETH, 18 dec)
WBNB = '0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c'
# PancakeSwap V3 ETH/WBNB pools (factory 0x0BFbCF9f... getPool; token0 = ETH in both). The first prices the market.
POOLS = ['0xD0e226f674bBf064f54aB47F42473fF80DB98CBA',   # 0.05 pct, 4,675 ETH + 5,619 WBNB on 2026-11-22
         '0x62Fcb3C1794FB95BD8B1A97f6Ad5D8a7e4943a1e']   # 0.01 pct, 323 ETH + 354 WBNB
P_USDT_WBNB_PCS = '0x172fcd41e0913e95784454622d1c3724f546f849'   # PancakeSwap V3 USDT/WBNB 0.01 pct (token0 USDT)

# selectors: output of `cast sig` (selftest.py checks every one, and the run() encoding, against cast)
_SELS = {
    'amountAvailableForTrading(address)': '0xeec245e2',
    'expectedTradeInput(address,uint128)': '0xa7ae00d2',
    'slot0()': '0x3850c7bd',
    'run(address,address,address,address,uint128,uint128,uint256)': '0x2621f7f8',
}

PAPER_EXEC = '0xb464f7314d55ec6a9a0cf6f7f6df17af8ed5b352'   # fork deployment; paper code override only
PAPER_OWNER = '0xc0ffee0000000000000000000000000000000001'
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

# ---- when to take ---------------------------------------------------------------------------
HALF_LIFE = 43200              # priceDecayHalfLife() of the Vortex, seconds
MIN_DISCOUNT_BPS = 300         # take when the ask is 3 pct under the pool price. The one past taker let two of three
                               # native lots fall 10 and 20 pct under; the third went at 0.25 pct (README).
MIN_LOT_WEI = 5 * 10**16       # ignore lots under 0.05 BNB (3 pct of that is under a cent)
# ---- loss guard -----------------------------------------------------------------------------
# BSC has no base fee and no L1 fee: the worst case of one send is gasLimit x gasPrice, both signed.
MAX_TX_USD = 0.90              # gasLimit x gasPrice at the pool's BNB/USD x PRICE_MARGIN stays under this
PRICE_MARGIN = 1.15
BNB_USD_MIN, BNB_USD_MAX = 100.0, 5000.0   # a pool price outside this band is treated as unreadable: no send
MAX_FEE_WEI = 1_000_000_000    # 1 gwei absolute ceiling for the gas price (the chain's price is about 0.05 gwei)
MAX_GAS_LIMIT = 800_000        # fork: 277,552 used
SIM_GAS = 800_000
GAS_PRICE_MULT = 2             # gas price = 2 x eth_gasPrice: no bidding war, just not the last in the block
MIN_GAIN_OVER_CAP = 5          # the simulated gain must be at least 5 x the signed gas cap
KEEP_SHARE_PCT = 90            # minProfit = 90 pct of the simulated gain (the pool can move a little), never under cap + 1
SEND_COOLDOWN = 120
# ---- sleeping -------------------------------------------------------------------------------
MAX_SLEEP = 6 * 3600           # look at least every 6 h: catches a reset, a new lot, a BNB/ETH move
MIN_SLEEP = 20                 # never faster than one look per 20 s
RELAY_CU_CAP = 20_000          # per UTC day
CU_COST = {'eth_call': 26, 'eth_estimateGas': 20, 'eth_getTransactionReceipt': 20, 'eth_gasPrice': 20, 'eth_getBalance': 20}
BLOCK = 'latest'
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


def view(to, data):
    return rpc('eth_call', [{'to': to, 'data': data}, BLOCK])


def lot():
    """native wei the Vortex offers now"""
    return int(view(VORTEX, _SELS['amountAvailableForTrading(address)'] + aword(NATIVE)), 16)


def ask(amount):
    """Binance-Peg ETH wei the auction charges for `amount` native now (reverts when trading is off)"""
    return int(view(VORTEX, _SELS['expectedTradeInput(address,uint128)'] + aword(NATIVE) + word(amount)), 16)


def wbnb_per_eth():
    sqrt_p = int(view(POOLS[0], _SELS['slot0()'])[2:66], 16)
    if sqrt_p == 0:
        raise RuntimeError('ETH/WBNB pool unreadable')
    return sqrt_p * sqrt_p / 2**192      # token1 (WBNB) per token0 (ETH), both 18 decimals


def bnb_usd():
    """USDT per WBNB from slot0 of the PancakeSwap V3 USDT/WBNB 0.01 pct pool (token0 USDT, token1 WBNB, both 18 dec)."""
    sqrt_p = int(view(P_USDT_WBNB_PCS, _SELS['slot0()'])[2:66], 16)
    if sqrt_p == 0:
        raise RuntimeError('BNB/USD pool unreadable')
    price = 2**192 / (sqrt_p * sqrt_p)
    if not BNB_USD_MIN < price < BNB_USD_MAX:
        raise RuntimeError(f'BNB/USD {price} outside the plausible band')
    return price


def calldata(pool, amount, max_input, min_profit):
    return (_SELS['run(address,address,address,address,uint128,uint128,uint256)'] + aword(VORTEX) + aword(pool) + aword(ETH)
            + aword(WBNB) + word(amount) + word(max_input) + word(min_profit))


def sim(data, ctx, gas=SIM_GAS):
    frm, to, ov = ctx
    params = [{'from': frm, 'to': to, 'data': data, 'gas': hex(gas)}, BLOCK] + ([ov] if ov else [])
    return int(rpc('eth_call', params)[2:66], 16)


def try_sim(data, ctx, gas=SIM_GAS):
    try:
        return sim(data, ctx, gas)
    except ReadBudgetExceeded:
        raise
    except RuntimeError:
        return None    # executor revert: the take does not pay


def estimate(data, ctx):
    frm, to, ov = ctx
    params = [{'from': frm, 'to': to, 'data': data}, BLOCK] + ([ov] if ov else [])
    return int(rpc('eth_estimateGas', params), 16)


def send_live(data, gas_limit, gas_price, gross, min_profit, cap_wei, amount, pool):
    import farmbot_signer
    # BSC has no base fee: maxFeePerGas = maxPriorityFeePerGas = the gas price
    reply = farmbot_signer.send(CHAIN, EXEC, data, 0, gas_limit, gas_price, max_priority_fee_per_gas=gas_price)
    h = None
    if isinstance(reply, dict):
        h = reply.get('txHash') or reply.get('tx_hash') or reply.get('hash')
    if not h:
        log('signer_reject', reply=reply, amount=amount)   # final, never retried
        return
    log('send', hash=h, pool=pool, amount=amount, gas_limit=gas_limit, max_fee=gas_price, priority=gas_price,
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
        log('send_result', hash=h, result='unknown', gas_used=None)
        return
    status = int(receipt['status'], 16)
    used = int(receipt['gasUsed'], 16)
    cost = used * int(receipt['effectiveGasPrice'], 16)
    log('send_result', hash=h, result='won' if status else 'lost', gas_used=used, gas_cost_wei=cost,
        send_block=int(receipt['blockNumber'], 16), expected_gross_wei=gross, net_wei=(gross - cost if status else -cost),
        amount=amount)


def take(s, amount, need, ctx, now):
    """The ask is under the line: pick the pool, cap the gas, guard, then send or paper-log."""
    rows = {p: try_sim(calldata(p, amount, need, 1), ctx) for p in POOLS}
    best = [(p, g) for p, g in rows.items() if g]
    if not best:
        log('opportunity_skip', reason='every_pool_reverts', sims=rows, amount=amount, ask_wei=need)
        return False
    pool, gross = max(best, key=lambda x: x[1])
    try:
        est = estimate(calldata(pool, amount, need, 1), ctx)
        price = bnb_usd()
    except RuntimeError as e:
        log('opportunity_skip', reason='estimate_or_price_failed', error=str(e)[:160], amount=amount, gross_wei=gross)
        return False
    chain_price = int(rpc('eth_gasPrice', []), 16)
    gas_limit = est * 12 // 10 + 50_000
    usd_ceiling = int(MAX_TX_USD / (price * PRICE_MARGIN) * 1e18 / gas_limit) - 1
    gas_price = min(chain_price * GAS_PRICE_MULT, MAX_FEE_WEI, usd_ceiling)
    cap_wei = gas_limit * gas_price                      # the signed worst case of one send
    cap_usd = cap_wei / 1e18 * price
    min_profit = max(gross * KEEP_SHARE_PCT // 100, cap_wei + 1)
    log('opportunity', sims=rows, pool=pool, amount=amount, ask_wei=need, gross_wei=gross, gross_usd=gross / 1e18 * price,
        chain_gas_price=chain_price, gas_estimate=est, gas_limit=gas_limit, gas_price=gas_price, gas_cap_wei=cap_wei,
        gas_cap_usd=cap_usd, bnb_usd=price, min_profit_wei=min_profit)
    if gas_price < chain_price or gas_limit > MAX_GAS_LIMIT or cap_usd * PRICE_MARGIN >= MAX_TX_USD:
        log('opportunity_skip', reason='fee_gas_or_usd_cap', gas_price=gas_price, chain_gas_price=chain_price,
            gas_limit=gas_limit, gas_cap_usd=cap_usd)
        return False
    if gross < cap_wei * MIN_GAIN_OVER_CAP:
        log('opportunity_skip', reason='gross_below_5x_gas_cap', gross_wei=gross, gas_cap_wei=cap_wei)
        return False
    if s.get('cooldown', 0) > now:
        log('opportunity_skip', reason='cooldown')
        return False
    data = calldata(pool, amount, need, min_profit)
    checked = try_sim(data, ctx, gas_limit)      # the exact guarded call at the signed gas limit
    if not checked:
        log('simulate_revert', amount=amount, min_profit_wei=min_profit, gas_limit=gas_limit)
        return False
    s['cooldown'] = now + SEND_COOLDOWN
    if MODE == 'live':
        balance = int(rpc('eth_getBalance', [ctx[0], 'latest']), 16)
        if balance < cap_wei:
            log('opportunity_skip', reason='wallet_below_gas_cap', wallet_wei=balance, gas_cap_wei=cap_wei)
            return False
        send_live(data, gas_limit, gas_price, checked, min_profit, cap_wei, amount, pool)
    else:
        log('paper_sim', result='success', pool=pool, amount=amount, gross_wei=checked, min_profit_wei=min_profit,
            gas_limit=gas_limit, gas_price=gas_price, gas_cap_wei=cap_wei, net_wei_at_cap=checked - cap_wei,
            bnb_usd=price, gas_cap_usd=cap_usd)
    return True


def check(s):
    """One look at the chain. Returns the seconds to sleep before the next look."""
    now = time.time()
    amount = lot()
    if amount < MIN_LOT_WEI:
        log('check', reason='no_lot', lot_wei=amount)
        return MAX_SLEEP
    try:
        need = ask(amount)
    except RuntimeError as e:
        log('check', reason='ask_unreadable', lot_wei=amount, error=str(e)[:160])
        return MAX_SLEEP
    market = amount / wbnb_per_eth()                     # ETH wei the lot is worth at the pool's spot price
    ratio = need / market
    line = (10000 - MIN_DISCOUNT_BPS) / 10000
    if ratio > line:
        seconds_left = math.log2(ratio / line) * HALF_LIFE
        eta = datetime.datetime.fromtimestamp(now + seconds_left, datetime.timezone.utc).isoformat(timespec='seconds')
        log('check', reason='ask_above_line', lot_wei=amount, ask_wei=need, market_wei=int(market), ask_over_market=ratio,
            seconds_to_line=round(seconds_left), eta_utc=eta)
        # half the remaining time each look: converges on the crossing even when BNB/ETH moves, a handful of looks a day
        return min(MAX_SLEEP, max(MIN_SLEEP, seconds_left / 2))
    log('check', reason='ask_under_line', lot_wei=amount, ask_wei=need, market_wei=int(market), ask_over_market=ratio)
    take(s, amount, need, exec_ctx(), now)
    return 60    # taken, lost or skipped: look again in a minute (a taken lot shows as no_lot and the bot goes back to 6 h)


def load_state():
    try:
        return json.loads(STATE.read_text())
    except Exception:
        return {'cooldown': 0}


def save_state(s):
    tmp = STATE.with_suffix('.tmp')
    tmp.write_text(json.dumps(s, separators=(',', ':')))
    tmp.replace(STATE)


def main():
    s = load_state()
    log('start', mode=MODE, executor=(EXEC if MODE == 'live' else PAPER_EXEC), vortex=VORTEX, min_discount_bps=MIN_DISCOUNT_BPS)
    while True:
        wait = 60
        try:   # every RPC read of the bot happens inside this try (ReadBudgetExceeded sleeps to 00:00 UTC)
            wait = check(s)
        except ReadBudgetExceeded as e:
            log('read_budget', error=str(e))
            tomorrow = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=1)).replace(hour=0, minute=0, second=5, microsecond=0)
            wait = max(60, (tomorrow - datetime.datetime.now(datetime.timezone.utc)).total_seconds())
        except Exception as e:
            log('loop_error', error=str(e)[:250])
            wait = 60
        save_state(s)
        time.sleep(wait)


if __name__ == '__main__':
    main()
