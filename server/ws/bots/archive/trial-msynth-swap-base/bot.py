#!/usr/bin/env python3
"""trial: Metronome Synth on Base lets anyone swap one synth for another at the protocol's oracle price
(Pool.swap(synthIn, synthOut, amountIn), swap fee 10 pct of the output at the moment). msUSD and msETH both trade
far under their pegs on Aerodrome (msUSD about 0.80 USDC, msETH about 0.87 WETH), and when ETH moves the pool ratio
msETH / msUSD drifts above the oracle rate plus the fee. Then the round trip
  USDC -> msUSD (Aerodrome pool), Pool.swap(msUSD -> msETH), msETH -> WETH (Aerodrome pool), WETH -> USDC (Uniswap V3)
pays. One transaction through the SynthLoop executor with a free Morpho flash loan of USDC; it reverts unless its
USDC balance grew by minProfit, and sends all USDC to the bot wallet. No principal.
Timer bot: every POLL seconds the exact run() is simulated as an eth_call for two pool sets (the Solidly-style pools
the incumbent uses, and the Slipstream pools); a revert means no gap. Only a gain above MIN_INTEREST looks further
(the two mixed pool sets, larger sizes) and sends."""
import sys
sys.path.append('/opt/farm/lib')
import datetime
import json
import os
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
MODE = os.environ.get('BOT_MODE', 'paper')
RELAY = os.environ.get('RPC_RELAY_URL', 'http://127.0.0.1:8545').rstrip('/')
LANE = os.environ.get('RPC_LANE', 'paper')
CHAIN = 'base'

# Addresses: synth pool and synths from KB protocols:891 (Metronome's deployment, getters answered), pools from the
# incumbents' receipts (tx 0xfebbbdc3..., 0x929d7052...); token0 / token1 / fee of each pool read on chain 2026-11-23
# (scratch/ra0c6/facts.py) and again by the proof script.
USDC = '0x833589fcd6edb6e08f4c7c32d4f71b54bda02913'
WETH = '0x4200000000000000000000000000000000000006'
MSUSD = '0x526728dbc96689597f85ae4cd716d4f7fccbae9d'
MSETH = '0x7ba6f01772924a82d9626c126347a28299e98c98'
SYNTH_POOL = '0xc614136d6c5ab85bc2acf0ec2652351642d7f54e'   # Metronome Synth Pool (proxy): swap / quoteSwapOut
MORPHO = '0xbbbbbbbbbb9cc5e90e3b3af64bdaf62c37eeffcb'       # Morpho Blue: flashLoan, no fee
P1_V2 = '0xcefc8b799a8ee5d9b312aeca73262645d664aaf7'        # Aerodrome stable pool msUSD / USDC
P1_CL = '0xbac7394c3c4b2d188d4180275ef6dd629f4c56ff'        # Slipstream msUSD / USDC, fee 320 ppm
P3_V2 = '0xde4fb30ccc2f1210fce2c8ad66410c586c8d1f9a'        # Aerodrome stable pool WETH / msETH
P3_CL = '0x34b6d0c67db6ddeb231e6fee78558b89157c5e7a'        # Slipstream WETH / msETH, fee 332 ppm
P4 = '0xb4cb800910b228ed3d0834cf79d697127bbb00e5'           # Uniswap V3 WETH / USDC, fee 100 ppm
# (pool1, v3 flag, pool3, v3 flag): the first two are simulated at every look
COMBOS = [('v2v2', P1_V2, False, P3_V2, False), ('clcl', P1_CL, True, P3_CL, True),
          ('v2cl', P1_V2, False, P3_CL, True), ('clv2', P1_CL, True, P3_V2, False)]

# Selectors and topics from `cast sig` / `cast keccak` (2026-11-23).
SEL_RUN = '0x1b9620ec'      # run((address,address,address,address,address,address,address,address,address,bool,bool,bool,uint256,uint256))
TOPIC_SWAPPED = '0xafd74f009c0ff7627726f24b568ee5529cd297f6a7a1e43ec363443a13a58420'  # SyntheticTokenSwapped(address,address,address,uint256,uint256,uint256)

PAPER_EXEC = '0x00000000000000000000000000000000000d00a6'   # code-override address, paper only
PAPER_OWNER = '0xc0ffee0000000000000000000000000000000321'  # owner baked into the fork deployment's runtime code
EXEC = os.environ.get('EXECUTOR_ADDR_BASE') or os.environ.get('EXECUTOR_ADDR')
if MODE == 'live' and not EXEC:
    raise SystemExit('EXECUTOR_ADDR_BASE or EXECUTOR_ADDR required in live mode')
RUNTIME_FILE = HERE / 'executor-runtime.hex'

POLL = 60                          # seconds between looks (two eth_calls each)
BASE_SIZE = 400                    # USDC flash size of the look (the incumbents borrow 240-1,050 msUSD worth a take)
SIZES = [800, 1200, 1600, 2400]    # larger sizes tried on a hit; stops when the gain stops growing (the gap is shallow)
MIN_INTEREST = 30_000              # 0.03 USDC: smaller gains are not worth a send
SEND_MULT_NUM, SEND_MULT_DEN = 13, 10   # send when gross > 1.3 x the send's gas cap
TIP_SHARE_DEN = 10                 # priority fee: at most 1/10 of gross spread over the gas limit ...
TIP_MAX_WEI = 10**8                # ... and never above 0.1 gwei
MAX_FEE_CAP_WEI = 15 * 10**7       # never sign above 0.15 gwei
GAS_LIMIT_MAX = 2_400_000          # 2.4M x 0.15 gwei = 0.00036 ETH = 0.90 USD at the reference price
L1_FEE_ALLOW_WEI = 2 * 10**12      # allowance for the OP Stack L1 data fee
ETH_REF_USD = 2500.0               # USD cap reference, well above the price (about 1,710 USD on 2026-11-23)
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


def run_calldata(combo, amount, min_profit):
    _, p1, v1, p3, v3 = combo
    words = [a(MORPHO), a(SYNTH_POOL), a(USDC), a(MSUSD), a(MSETH), a(WETH), a(p1), a(p3), a(P4),
             w(1 if v1 else 0), w(1 if v3 else 0), w(1), w(amount), w(min_profit)]
    return SEL_RUN + ''.join(words)


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


def gain_of(combo, amount, min_profit, gas_limit=None, block='latest'):
    """Return value of the exact run() as an eth_call (USDC units gained); 0 when it reverts."""
    ans = rpc('eth_call', call_params(run_calldata(combo, amount, min_profit), gas_limit, block), raw=True)
    if 'error' in ans and 'revert' not in str(ans['error']):
        raise RuntimeError('eth_call: ' + str(ans['error'])[:200])   # a relay or quota error is not "no gap": loop_error line
    if 'error' in ans or not ans.get('result') or ans['result'] == '0x':
        return 0, str(ans.get('error'))[:160]
    return int(ans['result'], 16), None


def best_take(first_combo, first_gain):
    """After a hit at BASE_SIZE: the two mixed pool sets at BASE_SIZE, then larger sizes on the best set.
    Returns (combo, amount in USDC units, gain)."""
    best = (first_combo, BASE_SIZE * 10**6, first_gain)
    for combo in COMBOS:
        if combo[0] == first_combo[0]:
            continue
        gain, _ = gain_of(combo, BASE_SIZE * 10**6, 1)
        if gain > best[2]:
            best = (combo, BASE_SIZE * 10**6, gain)
    for s in SIZES:
        gain, _ = gain_of(best[0], s * 10**6, 1)
        if gain <= best[2]:
            break
        best = (best[0], s * 10**6, gain)
    return best


def last_swap_block(block):
    """Block of the newest synth swap at the Pool near our send: the winner's block when we lost."""
    logs = rpc('eth_getLogs', [{'address': SYNTH_POOL, 'fromBlock': hex(block - 300), 'toBlock': hex(block + 10),
                               'topics': [TOPIC_SWAPPED]}])
    return max((int(x['blockNumber'], 16) for x in logs), default=None)


def send_live(combo, amount, gross, cap_usdc, max_fee, tip, gas_limit):
    import farmbot_signer
    reply = farmbot_signer.send(CHAIN, EXEC, run_calldata(combo, amount, cap_usdc), 0, gas_limit, max_fee, max_priority_fee_per_gas=tip)
    tx_hash = reply.get('txHash') if isinstance(reply, dict) else None
    if not tx_hash:
        log('signer_reject', reply=reply)
        return
    receipt = None
    for _ in range(20):
        time.sleep(1.0)
        receipt = rpc('eth_getTransactionReceipt', [tx_hash])
        if receipt:
            break
    common = dict(hash=tx_hash, pools=combo[0], amount_usdc=amount, expected_gross_usdc=gross,
                  cap_usdc=cap_usdc, gas_limit=gas_limit, max_fee_wei=max_fee, tip_wei=tip)
    if not receipt:
        log('send_result', result='unknown', gas_used=None, winner_block=None, **common)
        return
    block = int(receipt['blockNumber'], 16)
    status = int(receipt['status'], 16)
    used = int(receipt['gasUsed'], 16)
    cost = used * int(receipt['effectiveGasPrice'], 16) + int(receipt.get('l1Fee') or '0x0', 16)
    try:
        winner = block if status else last_swap_block(block)
    except Exception as e:
        log('winner_lookup_error', hash=tx_hash, error=str(e)[:160])
        winner = None
    log('send_result', result='won' if status else 'lost', gas_used=used, gas_cost_wei=cost,
        gross_usdc=gross if status else 0, send_block=block, winner_block=winner,
        tx_index=int(receipt['transactionIndex'], 16), **common)


_last_paper = [0.0]


def check():
    """One look: 2 eth_calls when there is no gap. Returns True when a gain above MIN_INTEREST was seen."""
    hit = None
    for combo in COMBOS[:2]:
        gain, _ = gain_of(combo, BASE_SIZE * 10**6, 1)
        if gain >= MIN_INTEREST and (hit is None or gain > hit[1]):
            hit = (combo, gain)
    if hit is None:
        return False
    combo, amount, gross = best_take(*hit)
    base_fee = int(rpc('eth_getBlockByNumber', ['latest', False])['baseFeePerGas'], 16)
    try:
        estimate = int(rpc('eth_estimateGas', call_params(run_calldata(combo, amount, 1))), 16)
    except Exception as e:
        log('simulate_revert', step='estimate', pools=combo[0], gross_usdc=gross, error=str(e)[:200])
        return True
    gas_limit = estimate * 12 // 10
    gross_wei = int(gross / 1e6 / ETH_REF_USD * 1e18)             # gross in wei at the reference price (a low value)
    tip = min(TIP_MAX_WEI, gross_wei // TIP_SHARE_DEN // gas_limit)
    max_fee = base_fee + base_fee // 4 + tip
    cap = gas_limit * max_fee + L1_FEE_ALLOW_WEI                  # the most this send should cost
    cap_usd = cap / 1e18 * ETH_REF_USD
    cap_usdc = int(cap_usd * 1e6) + 1                             # the same in USDC units = the tx's minProfit
    log('opportunity', pools=combo[0], amount_usdc=amount, gross_usdc=gross, cap_usdc=cap_usdc, base_fee=base_fee,
        tip_wei=tip, max_fee_wei=max_fee, gas_estimate=estimate, gas_limit=gas_limit, cap_usd=round(cap_usd, 4))
    if max_fee > MAX_FEE_CAP_WEI or gas_limit > GAS_LIMIT_MAX or cap_usd >= MAX_TX_USD:
        log('opportunity_skip', reason='fee_gas_or_usd_cap', max_fee_wei=max_fee, gas_limit=gas_limit, cap_usd=cap_usd)
        return True
    if gross * SEND_MULT_DEN <= cap_usdc * SEND_MULT_NUM:         # send only when expected gross > 1.3 x this send's gas cap
        log('opportunity_skip', reason='gross_below_send_line', gross_usdc=gross, cap_usdc=cap_usdc)
        return True
    checked, err = gain_of(combo, amount, cap_usdc, gas_limit)    # the exact call that would be signed (minProfit = gas cap)
    if checked <= cap_usdc:
        log('simulate_revert', step='guard', pools=combo[0], gross_usdc=gross, cap_usdc=cap_usdc, error=err)
        return True
    if MODE == 'paper':
        log('paper_sim', result='success', pools=combo[0], amount_usdc=amount, gross_usdc=checked,
            cap_usdc=cap_usdc, gas_estimate=estimate, gas_limit=gas_limit, max_fee_wei=max_fee, tip_wei=tip)
        _last_paper[0] = time.time()
    else:
        send_live(combo, amount, checked, cap_usdc, max_fee, tip, gas_limit)
    return True


def main():
    """Timer loop. Every relay read is inside the try that catches the bot's CU cap."""
    if MODE == 'paper' and not RUNTIME_FILE.exists():
        raise SystemExit('missing executor-runtime.hex (paper code override)')
    log('start', mode=MODE, executor=executor(), synth_pool=SYNTH_POOL, pool_sets=[c[0] for c in COMBOS], poll_seconds=POLL)
    next_poll = 0
    looks = 0
    while True:
        try:
            now = time.time()
            if now >= next_poll:
                next_poll = now + POLL
                seen = check()
                looks += 1
                if looks % 60 == 1 and not seen:
                    log('heartbeat', looks=looks)
                if seen and MODE == 'live':
                    next_poll = time.time() + 10   # part of the gap may be left, or the send lost: look again soon
                if seen and MODE == 'paper':
                    next_poll = time.time() + 300  # paper sends nothing, the gap stays: do not re-log it every look
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
