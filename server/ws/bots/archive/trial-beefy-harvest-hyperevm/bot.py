#!/usr/bin/env python3
"""Trial: Beefy cowcentrated strategy harvest caller fee on HyperEVM through the BeefyHarvestTake executor.

Each Beefy CLM strategy pays a WHYPE caller fee to whoever calls its public harvest(address). The fee
grows with pool volume since the last harvest. One transaction through the executor calls harvest
with the executor as fee recipient, unwraps the WHYPE and pays it to the bot wallet as native HYPE;
it reverts unless the wallet receives at least minProfit, which the bot sets to that send's whole gas
cap (gas limit x maxFeePerGas). A lost attempt costs gas only.

Timer bot, no feed: every strategy is simulated by eth_call on its own schedule (the next check is
placed where the accrual rate says the fee reaches the send threshold; 30 s to 30 min apart).
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

WHYPE = '0x5555555555555555555555555555555555555555'
# The 9 active Beefy CLM strategy proxies (Beefy vault API, KB lead 318); call arguments of the executor.
STRATS = ['0x6dd1c86d0f3163767917515512ca03add8520192', '0xaacd20dae543a03e0f7cd2bec77190120017a956',
          '0x92e3b9abc8f80ee32bf12a3ebdd225d2929c878a', '0x2cdc091724b45ea6408ab4a12af520da8e0c9fcf',
          '0x2bbcf0cefed10329e03350bc2a8ed7ffdf3955fc', '0x68e15d60d789bc8b08a36152a37b8c55dd5436f0',
          '0x5423980fd996ff1014cf275c1ed9d75d14ee67a9', '0xb8d764eea0d42295f4874070c0a6cecf55bed07b',
          '0x9609242a9b01b5d56bb3879bc86f65ddef3a6a2e']
SEL_TAKE = '0xb4668090'       # cast sig "take(address,address,uint256,uint256,uint256)"
T_CHARGED = '0xd255b592c7f268a73e534da5219a60ff911b4cf6daae21c7d20527dd657bd99a'  # cast keccak ChargedFees(uint256,uint256,uint256)

PAPER_EXEC = '0x8f7a45ebde059392e46a46dcc14ab24681a961ea'    # fork deployment; paper code override only
PAPER_OWNER = '0x1111111111111111111111111111111111111111'   # the owner baked into that deployment
EXEC = os.environ.get('EXECUTOR_ADDR_HYPEREVM') or os.environ.get('EXECUTOR_ADDR')
if MODE == 'live' and not EXEC:
    raise SystemExit('EXECUTOR_ADDR_HYPEREVM or EXECUTOR_ADDR is required in live mode')
RUNTIME = (HERE / 'executor-runtime.hex').read_text().strip()
if not RUNTIME.startswith('0x'):
    raise SystemExit('missing paper executor runtime')
LOG = HERE / 'logs' / 'bot.jsonl'
STATE = HERE / 'state' / 'state.json'
CU_FILE = HERE / 'state' / 'cu.json'
LOG.parent.mkdir(exist_ok=True)
STATE.parent.mkdir(exist_ok=True)

# ---- loss guard (trial rule: every send's gas limit x maxFeePerGas < 1 USD) ----
GAS_HARD_LIMIT = 1_950_000     # chain cap 2,000,000
MAX_FEE_WEI = 5 * 10**8        # hard ceiling on maxFeePerGas, 0.5 gwei: 1.95M x 0.5 gwei = 0.000975 HYPE
                               # (under 1 USD while HYPE is under 1,025 USD; the signer checks the USD value too)
SIM_GAS = 1_950_000
GAS_PAD = 30_000               # intrinsic + calldata on top of the executor's own measured gas
GAS_MARGIN = 1.04              # fork: limit 1,073,707 from inner 1,002,411 succeeded, gasUsed 837,046 after refunds
FEE_MARGIN = 1.03              # maxFeePerGas = base fee x 1.03 + priority
BID_SHARE = 0.20               # priority bid = at most 20% of (gross - gas cap at the base fee)
MIN_GAP_S, MAX_GAP_S = 30, 1800
REVERT_GAP_S = 1800            # a strategy whose harvest reverts (not calm, broken reward route)
AFTER_SEND_GAP_S = 120
PAPER_AFTER_OPP_GAP_S = 600    # paper takes nothing, so the same fee stays: do not log it every 30 s
CU_COST = {'eth_call': 26, 'eth_getLogs': 75, 'eth_getTransactionReceipt': 20, 'eth_getBlockByNumber': 20}
CU_CAP = 90_000                # relay CU/day, hard cap in code (trial rule: <= 100,000)
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


def calldata(strategy, min_profit, max_gas_price, deadline):
    return SEL_TAKE + aw(strategy) + aw(WHYPE) + word(min_profit) + word(max_gas_price) + word(deadline)


def signer():
    if '/opt/farm/lib' not in sys.path:
        sys.path.append('/opt/farm/lib')
    import farmbot_signer
    return farmbot_signer


def owner():
    a = signer().my_address()
    a = a['address'] if isinstance(a, dict) else a
    if not isinstance(a, str) or len(a) != 42:
        raise RuntimeError('signer my_address returned no address')
    return a


def sim(strategy, min_profit, max_gas_price, deadline):
    """eth_call of the exact take(); returns (native gain in wei, gas spent inside the executor)."""
    from_addr = owner() if MODE == 'live' else PAPER_OWNER
    exec_addr = EXEC if MODE == 'live' else PAPER_EXEC
    tx = {'from': from_addr, 'to': exec_addr, 'data': calldata(strategy, min_profit, max_gas_price, deadline),
          'gas': hex(SIM_GAS)}
    params = [tx, 'latest'] + ([] if MODE == 'live' else [{exec_addr: {'code': RUNTIME}}])
    out = rpc('eth_call', params)
    return int(out[2:66], 16), int(out[66:130], 16)


def base_fee():
    blk = rpc('eth_getBlockByNumber', ['latest', False])
    return int(blk['baseFeePerGas'], 16)


def last_harvest_block(strategy, send_block):
    """Block of the latest ChargedFees of this strategy at or before our send (the winner's block)."""
    logs = rpc('eth_getLogs', [{'address': strategy, 'fromBlock': hex(max(0, send_block - 600)),
                               'toBlock': hex(send_block), 'topics': [T_CHARGED]}])
    return max((int(x['blockNumber'], 16) for x in logs), default=None)


def send_live(strategy, data, gas_limit, max_fee, priority, gain):
    reply = signer().send(CHAIN, EXEC, data, 0, gas_limit, max_fee, max_priority_fee_per_gas=priority)
    h = reply.get('txHash') if isinstance(reply, dict) else None
    if not h:
        log('signer_reject', strategy=strategy, reply=reply)       # final: no retry
        return
    receipt = None
    for _ in range(25):
        time.sleep(1.0)
        receipt = rpc('eth_getTransactionReceipt', [h])
        if receipt:
            break
    if not receipt:
        log('send_result', hash=h, strategy=strategy, result='unknown', gas_used=None, winner_block=None)
        return
    b = int(receipt['blockNumber'], 16)
    used = int(receipt['gasUsed'], 16)
    status = int(receipt['status'], 16)
    winner = b
    if not status:
        try:
            winner = last_harvest_block(strategy, b)
        except Exception:
            winner = None
    log('send_result', hash=h, strategy=strategy, result='won' if status else 'lost', gas_used=used,
        gas_cost_wei=used * int(receipt['effectiveGasPrice'], 16), send_block=b, winner_block=winner,
        blocks_after_winner=(b - winner if winner is not None else None), simulated_gain_wei=gain,
        gas_limit=gas_limit, max_fee=max_fee, priority=priority)


def check(strategy, st):
    """Simulate one strategy; send (live) or log (paper) when gross exceeds the send's gas cap.
    Returns the seconds until this strategy's next check."""
    now = time.time()
    deadline = int(now) + 120
    try:
        gain, inner = sim(strategy, 1, MAX_FEE_WEI, deadline)
    except ReadBudgetExceeded:
        raise
    except Exception as e:
        log('sim_revert', strategy=strategy, error=str(e)[:160])
        st.pop('prev', None)
        return REVERT_GAP_S
    gas_limit = int((inner + GAS_PAD) * GAS_MARGIN)
    base = base_fee()
    floor_cap = int(gas_limit * base * FEE_MARGIN)          # gas cap of a send at priority 0
    ratio = gain / floor_cap
    prev = st.get('prev')
    st['prev'] = [now, gain]
    log('sim', strategy=strategy, gain_wei=gain, inner_gas=inner, gas_limit=gas_limit, base_fee=base,
        floor_cap_wei=floor_cap, ratio=round(ratio, 4))
    if gain <= floor_cap or gas_limit > GAS_HARD_LIMIT or base * FEE_MARGIN > MAX_FEE_WEI:
        if gain > floor_cap:
            log('opportunity_skip', strategy=strategy, gain_wei=gain, gas_limit=gas_limit, base_fee=base,
                reason='gas_limit_over_chain_cap' if gas_limit > GAS_HARD_LIMIT else 'base_fee_above_fee_cap')
            return MAX_GAP_S
        # schedule: where the measured accrual rate puts the fee at the threshold (half of that, clamped)
        if prev and gain > prev[1] and now > prev[0]:
            eta = (floor_cap - gain) / ((gain - prev[1]) / (now - prev[0]))
            return max(MIN_GAP_S, min(MAX_GAP_S, eta * 0.5))
        return 600 if ratio > 0.5 else MAX_GAP_S
    priority = int(BID_SHARE * (gain - floor_cap) / gas_limit)
    max_fee = min(MAX_FEE_WEI, int(base * FEE_MARGIN) + priority)
    priority = min(priority, max_fee)
    cap = gas_limit * max_fee                                # this send's worst case; also its minProfit
    if gain <= cap:
        return MIN_GAP_S
    data = calldata(strategy, cap, max_fee, deadline)
    try:
        gain, _ = sim(strategy, cap, max_fee, deadline)      # the exact bytes that would be sent
    except ReadBudgetExceeded:
        raise
    except Exception as e:
        log('sim_revert', strategy=strategy, error=str(e)[:160], stage='exact')
        return MIN_GAP_S
    log('opportunity', strategy=strategy, gain_wei=gain, gas_limit=gas_limit, gas_cap_wei=cap, max_fee=max_fee,
        priority=priority, base_fee=base, mode=MODE)
    st.pop('prev', None)
    if MODE == 'live':
        send_live(strategy, data, gas_limit, max_fee, priority, gain)
        return AFTER_SEND_GAP_S
    log('paper_sim', strategy=strategy, result='success', gain_wei=gain, gas_cap_wei=cap,
        est_net_wei=gain - int((inner + GAS_PAD) * 0.82 * (base + priority)))
    return PAPER_AFTER_OPP_GAP_S


def main():
    try:
        s = json.loads(STATE.read_text())
    except Exception:
        s = {}
    log('start', mode=MODE, executor=EXEC if MODE == 'live' else PAPER_EXEC, strategies=len(STRATS),
        max_fee_wei=MAX_FEE_WEI, cu_cap=CU_CAP)
    while True:
        try:
            now = time.time()
            for strat in STRATS:
                st = s.setdefault(strat, {})
                if st.get('next', 0) > now:
                    continue
                gap = check(strat, st)
                st['next'] = time.time() + gap
                st['gap'] = gap
        except ReadBudgetExceeded as e:
            log('read_budget', error=str(e))
            time.sleep(600)
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
            log('relay_error', error=str(e)[:180])
            time.sleep(20)
        except Exception as e:
            log('loop_error', error=str(e)[:250])
            time.sleep(20)
        STATE.write_text(json.dumps(s))
        time.sleep(10)


if __name__ == '__main__':
    main()
