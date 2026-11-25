#!/usr/bin/env python3
"""trial: beHYPE (Hyperbeat liquid staking token) can be withdrawn instantly by anyone at the WithdrawManager:
withdraw(amount, true, minOut) pays native HYPE at StakingCore.BeHYPEToHYPE less the instant fee (30 bps), about 1.0218
HYPE a token. It also trades on thin V3-style WHYPE pools. When somebody sells beHYPE into the pools instead of
withdrawing (a liquidator, a router), the pools fall under the instant-withdrawal value. One transaction through the
InstantRedeemArb executor then: flash-swaps WHYPE for beHYPE on every pool that is below value (each pool stops at its
own price limit = instant value less the pool fee), withdraws all of it once, wraps the HYPE, pays the pools from it,
unwraps the rest and sends it to the bot wallet. No principal. The executor reverts unless it gained at least
minProfit. Timer bot: ONE Multicall3 eth_call every POLL seconds; the take is simulated only when a pool is below
value by more than MIN_GAP."""
import sys
sys.path.append('/opt/farm/lib')
import datetime
import json
import math
import os
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
MODE = os.environ.get('BOT_MODE', 'paper')
RELAY = os.environ.get('RPC_RELAY_URL', 'http://127.0.0.1:8545').rstrip('/')
LANE = os.environ.get('RPC_LANE', 'paper')
CHAIN = 'hyperevm'

VAULT = '0xd8fc8f0b03eba61f64d08b0bef69d80916e5dda9'       # beHYPE token (docs.hyperbeat.org addresses; KB protocols:458)
MANAGER = '0x9d0b0877b9f2204cf414ca7862e4f03506822538'     # WithdrawManager (same source); beHypeToken() = VAULT read on chain
CORE = '0xcead893b162d38e714d82d06a7fe0b0dc3c38e0b'        # StakingCore = WithdrawManager.stakingCore(), read on chain 2026-11-21
WHYPE = '0x5555555555555555555555555555555555555555'       # the pools' other token, read on chain 2026-11-21
MULTICALL3 = '0xca11bde05977b3631167028862be2a173976ca11'  # eth_getCode non-empty on hyperevm 2026-11-21
# The beHYPE / WHYPE V3 pools of the incumbents' receipts (tx 0x0ca5c314acbf..., 0x603480b070...); token0() and fee()
# are read on chain. (The Curve-style pool 0x2786cd87 is not used: it has no flash swap.)
# Two more fee-100 WHYPE pools found from the token's Transfer logs (scratch/trial-behype-redeem-hyperevm/pools.py).
POOLS = ['0x6801b1dbb4320c59af532ba4e34b2365d4a638be', '0xf777ead084b0f37080b55c0105b501567c91d369',
         '0x787afaedea38a8daa239e3478bf4fd01fa650b03', '0x2e603f13b32c5dcc46e91a2368599227641a1a10']

# Selectors and topic from `cast sig` / `cast keccak` (scratch/trial-behype-redeem-hyperevm/gen.py).
SEL_TAKE = '0xbd4c6d18'           # take(address,address,address,(address,bool,uint256,uint160)[],uint256)
SEL_SLOT0 = '0x3850c7bd'          # slot0()
SEL_FEE = '0xddca3f43'            # fee()
SEL_TOKEN0 = '0x0dfe1681'         # token0()
SEL_CONVERT = '0xa5c79dc8'        # StakingCore.BeHYPEToHYPE(uint256)
SEL_WFEE = '0x765b1687'           # WithdrawManager.instantWithdrawalFeeInBps()
SEL_WPAUSED = '0x5c975abb'        # WithdrawManager.paused()
SEL_AVAIL = '0xc5751b16'          # WithdrawManager.getTotalInstantWithdrawableBeHYPE()
SEL_AGG3 = '0x82ad56cb'           # aggregate3((address,bool,bytes)[])
TOPIC_PROCESSED = '0x6edbbde848a1a11cab349ede80a2845202b7bdf4e6c4273d095ffd08ce15b569'  # InstantWithdrawal(address,uint256,uint256,uint256)

PAPER_EXEC = '0x00000000000000000000000000000000000f11b0'   # code-override address, paper only
PAPER_OWNER = '0xc0ffee0000000000000000000000000000000321'  # owner baked into the fork deployment's runtime code
EXEC = os.environ.get('EXECUTOR_ADDR_HYPEREVM') or os.environ.get('EXECUTOR_ADDR')
if MODE == 'live' and not EXEC:
    raise SystemExit('EXECUTOR_ADDR_HYPEREVM or EXECUTOR_ADDR required in live mode')
RUNTIME_FILE = HERE / 'executor-runtime.hex'

POLL = 35                          # seconds between looks (one eth_call each)
MIN_GAP_PPM = 300                  # a pool counts when it is more than 0.03 pct below value after its fee
MIN_INTEREST_WEI = 10**15          # 0.001 HYPE (6 cents): smaller gains are not worth a send
MIN_WITHDRAW_WEI = 10**17          # WithdrawManager.minWithdrawalAmount() = 0.1 beHYPE, read on chain 2026-11-21
MAX_IN_WEI = 200 * 10**18          # most WHYPE one pool may take (the price limit stops it long before)
SEND_MULT_NUM, SEND_MULT_DEN = 13, 10   # send when gross > 1.3 x the send's gas cap
TIP_SHARE_DEN = 10                 # priority fee: at most 1/10 of gross spread over the gas limit ...
TIP_MAX_WEI = 2 * 10**9            # ... and never above 2 gwei
MAX_FEE_CAP_WEI = 7 * 10**9        # never sign above 7 gwei
GAS_LIMIT_MAX = 1_400_000          # hyperevm: every tx under 2,000,000; 1.4M x 7 gwei = 0.0098 HYPE
HYPE_REF_USD = 90.0                # USD cap reference, well above the price (60.40 USD on 2026-11-21)
MAX_TX_USD = 0.95
CU_CAP = 95_000
CU_COST = {'eth_call': 26, 'eth_getBlockByNumber': 20, 'eth_estimateGas': 20,
           'eth_getTransactionReceipt': 20, 'eth_blockNumber': 10, 'eth_getLogs': 75}

LOG = HERE / 'logs' / 'bot.jsonl'
STATE = HERE / 'state' / 'cu.json'


class ReadBudgetExceeded(Exception):
    pass


def log(event, **fields):
    LOG.parent.mkdir(exist_ok=True)
    with LOG.open('a') as f:
        f.write(json.dumps({'ts': round(time.time(), 3), 'ev': event, **fields}, separators=(',', ':')) + '\n')


def rpc(method, params, raw=False):
    day = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    try:
        budget = json.loads(STATE.read_text())
    except Exception:
        budget = {'day': day, 'cu': 0}
    if budget.get('day') != day:
        budget = {'day': day, 'cu': 0}
    budget['cu'] += CU_COST.get(method, 26)
    if budget['cu'] > CU_CAP:
        raise ReadBudgetExceeded(f'{CU_CAP} CU/day cap')
    STATE.parent.mkdir(exist_ok=True)
    STATE.write_text(json.dumps(budget))
    body = json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params}).encode()
    import urllib.request
    req = urllib.request.Request(f'{RELAY}/{CHAIN}?lane={LANE}', body, {'content-type': 'application/json'})
    with urllib.request.urlopen(req, timeout=40) as resp:
        ans = json.load(resp)
    if raw:
        return ans
    if 'error' in ans:
        raise RuntimeError(f'{method}: {str(ans["error"])[:300]}')
    return ans['result']


def w(n):
    return format(n, '064x')


def a(addr):
    return addr.lower().removeprefix('0x').zfill(64)


def agg3(calls, block='latest'):
    """aggregate3 with allowFailure = true; returns a list of (success, return bytes hex without 0x)."""
    items = []
    for target, data in calls:
        raw = data.removeprefix('0x')
        items.append(a(target) + w(1) + w(0x60) + w(len(raw) // 2) + raw + '00' * ((-(len(raw) // 2)) % 32))
    offs, pos = [], 32 * len(items)
    for it in items:
        offs.append(pos)
        pos += len(it) // 2
    data = SEL_AGG3 + w(32) + w(len(items)) + ''.join(w(o) for o in offs) + ''.join(items)
    res = rpc('eth_call', [{'to': MULTICALL3, 'data': data}, block]).removeprefix('0x')
    n = int(res[64:128], 16)
    base = 128
    out = []
    for i in range(n):
        off = int(res[base + 64 * i:base + 64 * (i + 1)], 16) * 2 + base
        ok = int(res[off:off + 64], 16) == 1
        ln = int(res[off + 128:off + 192], 16) * 2
        out.append((ok, res[off + 192:off + 192 + ln]))
    if len(out) != len(calls):
        raise RuntimeError('aggregate3: unexpected return length')
    return out


_static = {}   # pool -> (wnative is token0, fee in ppm); read once


def read_state(block='latest'):
    """One eth_call: instant-withdrawal value of one beHYPE (wei of HYPE, after the instant fee), the pause flag, how
    much beHYPE can be withdrawn instantly now, every pool's sqrtPriceX96. token0() and fee() of a pool are read the
    first time only."""
    need = [p for p in POOLS if p not in _static]
    calls = [(CORE, SEL_CONVERT + w(10**18)), (MANAGER, SEL_WFEE), (MANAGER, SEL_WPAUSED), (MANAGER, SEL_AVAIL)]
    calls += [(p, SEL_SLOT0) for p in POOLS]
    calls += [(p, SEL_TOKEN0) for p in need] + [(p, SEL_FEE) for p in need]
    out = agg3(calls, block)
    k = 4 + len(POOLS)
    for i, p in enumerate(need):
        ok0, t0 = out[k + i]
        okf, fee = out[k + len(need) + i]
        if ok0 and okf and len(t0) >= 64 and len(fee) >= 64:
            _static[p] = ('0x' + t0[24:64] == WHYPE, int(fee[:64], 16))
    for ok, ret in out[:4]:
        if not ok or len(ret) < 64:
            raise RuntimeError('withdraw manager getter failed')
    gross_rate, fee_bps = int(out[0][1][:64], 16), int(out[1][1][:64], 16)
    state = {'rate': gross_rate * (10**4 - min(fee_bps, 10**4)) // 10**4, 'gross_rate': gross_rate, 'wfee': fee_bps,
             'paused': int(out[2][1][:64], 16), 'avail': int(out[3][1][:64], 16), 'sqrt': {}}
    for p, (ok, ret) in zip(POOLS, out[4:k]):
        if ok and len(ret) >= 64 and p in _static:
            state['sqrt'][p] = int(ret[:64], 16)
    return state


def legs_of(state):
    """Pools that sell a share for less than it redeems for, after the pool fee, with the price limit where that
    stops being true. Returns (legs, widest gap in ppm). Integer math only for the limit."""
    if state['paused'] or state['rate'] == 0 or state['avail'] < MIN_WITHDRAW_WEI:
        return [], 0          # paused, or no instant liquidity / rate limit used up: stand down
    legs, widest = [], 0
    for p in POOLS:
        if p not in state['sqrt']:
            continue
        w_is0, fee = _static[p]
        sq = state['sqrt'][p]
        # value of a share bought on this pool at the margin: rate x (1 - fee); in the pool's price units:
        if w_is0:   # pool price = shares per WHYPE; buying shares pushes it DOWN to 1 / (rate x (1 - fee))
            limit = math.isqrt((10**18 * 10**6 << 192) // (state['rate'] * (10**6 - fee))) + 1
            gap_ppm = (sq * sq - limit * limit) * 10**6 // (sq * sq) if sq > limit else 0
        else:       # pool price = WHYPE per share; buying shares pushes it UP to rate x (1 - fee)
            limit = math.isqrt((state['rate'] * (10**6 - fee) << 192) // (10**18 * 10**6))
            gap_ppm = (limit * limit - sq * sq) * 10**6 // (limit * limit) if sq < limit else 0
        if gap_ppm > MIN_GAP_PPM:
            legs.append({'pool': p, 'zeroForOne': w_is0, 'limit': limit, 'gap_ppm': gap_ppm})
            widest = max(widest, gap_ppm)
    return legs, widest


def take_calldata(legs, min_profit):
    head = a(MANAGER) + a(VAULT) + a(WHYPE) + w(0xa0) + w(min_profit)
    body = w(len(legs)) + ''.join(a(l['pool']) + w(1 if l['zeroForOne'] else 0) + w(MAX_IN_WEI) + w(l['limit']) for l in legs)
    return SEL_TAKE + head + body


# ---- chain access ----
def owner():
    import farmbot_signer
    result = farmbot_signer.my_address()
    address = result['address'] if isinstance(result, dict) else result
    if not isinstance(address, str) or len(address) != 42:
        raise RuntimeError('signer my_address returned no address')
    return address


def executor():
    return EXEC if MODE == 'live' else PAPER_EXEC


def call_params(data, gas_limit=None, block='latest'):
    ex = executor()
    tx = {'from': owner() if MODE == 'live' else PAPER_OWNER, 'to': ex, 'data': data}
    if gas_limit is not None:
        tx['gas'] = hex(gas_limit)
    params = [tx, block]
    if MODE == 'paper':
        params.append({ex: {'code': RUNTIME_FILE.read_text().strip()}})
    return params


def gain_of(legs, min_profit, gas_limit=None, block='latest'):
    """Return value of the exact take() as an eth_call (wei of WHYPE gained); 0 when it reverts."""
    ans = rpc('eth_call', call_params(take_calldata(legs, min_profit), gas_limit, block), raw=True)
    if 'error' in ans or not ans.get('result') or ans['result'] == '0x':
        return 0, str(ans.get('error'))[:160]
    return int(ans['result'], 16), None


def last_redeem_block(block):
    """Block of the newest instant withdrawal at the manager near our send: the winner's block when we lost."""
    logs = rpc('eth_getLogs', [{'address': MANAGER, 'fromBlock': hex(block - 120), 'toBlock': hex(block + 5), 'topics': [TOPIC_PROCESSED]}])
    return max((int(x['blockNumber'], 16) for x in logs), default=None)


def send_live(legs, gross, cap, max_fee, tip, gas_limit):
    import farmbot_signer
    reply = farmbot_signer.send(CHAIN, EXEC, take_calldata(legs, cap), 0, gas_limit, max_fee, max_priority_fee_per_gas=tip)
    tx_hash = reply.get('txHash') if isinstance(reply, dict) else None
    if not tx_hash:
        log('signer_reject', reply=reply)
        return
    receipt = None
    for _ in range(20):
        time.sleep(1.5)
        receipt = rpc('eth_getTransactionReceipt', [tx_hash])
        if receipt:
            break
    common = dict(hash=tx_hash, pools=[l['pool'] for l in legs], expected_gross_wei=gross, cap_wei=cap,
                  gas_limit=gas_limit, max_fee_wei=max_fee, tip_wei=tip)
    if not receipt:
        log('send_result', result='unknown', gas_used=None, winner_block=None, **common)
        return
    block = int(receipt['blockNumber'], 16)
    status = int(receipt['status'], 16)
    used = int(receipt['gasUsed'], 16)
    cost = used * int(receipt['effectiveGasPrice'], 16)
    try:
        winner = block if status else last_redeem_block(block)
    except Exception as e:
        log('winner_lookup_error', hash=tx_hash, error=str(e)[:160])
        winner = None
    log('send_result', result='won' if status else 'lost', gas_used=used, gas_cost_wei=cost,
        net_wei=(gross - cost) if status else -cost, send_block=block, winner_block=winner,
        tx_index=int(receipt['transactionIndex'], 16), **common)


_dust = {}    # prices at the last look whose gain was below MIN_INTEREST


def check():
    """One look: 1 eth_call when no pool is below value. Returns True when a gain above MIN_INTEREST was seen."""
    state = read_state()
    legs, widest = legs_of(state)
    if not legs:
        return False
    key = (state['rate'], tuple(sorted(state['sqrt'].items())))
    if key == _dust.get('key'):
        return False          # same prices as the last look that was too small: no second call, no log line
    gross, err = gain_of(legs, 1)
    if gross < MIN_INTEREST_WEI:
        _dust['key'] = key
        log('check', result='below_interest', pools=len(legs), widest_gap_ppm=widest, chain_gain_wei=gross, error=err)
        return False
    base_fee = int(rpc('eth_getBlockByNumber', ['latest', False])['baseFeePerGas'], 16)
    try:
        estimate = int(rpc('eth_estimateGas', call_params(take_calldata(legs, 1))), 16)
    except Exception as e:
        log('simulate_revert', step='estimate', gross_wei=gross, error=str(e)[:200])
        return True
    gas_limit = estimate * 12 // 10
    tip = min(TIP_MAX_WEI, gross // TIP_SHARE_DEN // gas_limit)
    max_fee = base_fee + base_fee // 4 + tip
    cap = gas_limit * max_fee                     # the most this send can cost
    cap_usd = cap / 1e18 * HYPE_REF_USD
    log('opportunity', pools=[l['pool'] for l in legs], gaps_ppm=[l['gap_ppm'] for l in legs], rate_wei=state['rate'], fee_bps=state['wfee'], instant_avail_wei=state['avail'],
        gross_wei=gross, cap_wei=cap, base_fee=base_fee, tip_wei=tip, max_fee_wei=max_fee,
        gas_estimate=estimate, gas_limit=gas_limit, cap_usd=round(cap_usd, 4))
    if max_fee > MAX_FEE_CAP_WEI or gas_limit > GAS_LIMIT_MAX or cap_usd >= MAX_TX_USD:
        log('opportunity_skip', reason='fee_gas_or_usd_cap', max_fee_wei=max_fee, gas_limit=gas_limit, cap_usd=cap_usd)
        return True
    if gross * SEND_MULT_DEN <= cap * SEND_MULT_NUM:   # send only when expected gross > 1.3 x this send's gas cap
        log('opportunity_skip', reason='gross_below_send_line', gross_wei=gross, cap_wei=cap)
        return True
    checked, err = gain_of(legs, cap, gas_limit)   # the exact call that would be signed (minProfit = gas cap)
    if checked <= cap:
        log('simulate_revert', step='guard', gross_wei=gross, cap_wei=cap, error=err)
        return True
    if MODE == 'paper':
        log('paper_sim', result='success', pools=[l['pool'] for l in legs], gaps_ppm=[l['gap_ppm'] for l in legs],
            gross_wei=checked, cap_wei=cap, gas_estimate=estimate, gas_limit=gas_limit, max_fee_wei=max_fee, tip_wei=tip)
    else:
        send_live(legs, checked, cap, max_fee, tip, gas_limit)
    return True


def main():
    """Timer loop. Every relay read is inside the try that catches the bot's CU cap."""
    if MODE == 'paper' and not RUNTIME_FILE.exists():
        raise SystemExit('missing executor-runtime.hex (paper code override)')
    log('start', mode=MODE, executor=executor(), token=VAULT, manager=MANAGER, pools=len(POOLS), poll_seconds=POLL)
    next_poll = 0
    looks = 0
    while True:
        try:
            now = time.time()
            if now >= next_poll:
                next_poll = now + POLL
                seen = check()
                looks += 1
                if looks % 100 == 1 and not seen:
                    log('heartbeat', looks=looks)
                if seen and MODE == 'live':
                    next_poll = time.time() + 6    # part of the gap may be left, or the send lost: look again soon
                if seen and MODE == 'paper':
                    next_poll = time.time() + 600  # paper sends nothing, the gap stays: do not re-log it every look
            else:
                time.sleep(max(0.5, min(30, next_poll - now)))
        except ReadBudgetExceeded as e:
            log('read_budget', error=str(e))
            now = datetime.datetime.now(datetime.timezone.utc)
            time.sleep(86400 - (now.hour * 3600 + now.minute * 60 + now.second) + 5)   # to 00:00 UTC
        except Exception as e:
            log('loop_error', error=str(e)[:250])
            next_poll = time.time() + POLL
            time.sleep(5)


if __name__ == '__main__':
    main()
