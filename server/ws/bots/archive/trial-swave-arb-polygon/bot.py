#!/usr/bin/env python3
"""Trial: flash-funded SWAVE redeem at SetToken NAV against Polygon pool prices."""
import sys
sys.path.append('/opt/farm/lib')
import datetime
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
MODE = os.environ.get('BOT_MODE', 'paper')
RELAY = os.environ['RPC_RELAY_URL'].rstrip('/')
LANE = os.environ.get('RPC_LANE', 'paper')
CHAIN = 'polygon'
OWNER_PAPER = '0x1111111111111111111111111111111111111111'
EXEC_PAPER = '0x0000000000000000000000000000000000034901'
EXEC_LIVE = os.environ.get('EXECUTOR_ADDR_POLYGON') or os.environ.get('EXECUTOR_ADDR')
if MODE == 'live' and not EXEC_LIVE:
    raise SystemExit('EXECUTOR_ADDR_POLYGON or EXECUTOR_ADDR required')
RUNTIME = HERE / 'executor-runtime.hex'

# Source: explorer-verified SetToken/module; incumbent tx 0xddbc69d3... trace for the route.
MORPHO = '0x1bF0c2541F820E775182832f06c0B7Fc27A25f67'
USDC = '0x3c499c542cef5e3811e1192ce70d8cc03d5c3359'
WPOL = '0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270'
SWAVE = '0xd14d1e501b2b52d6134db1ad0857aa91f9bfe2dd'
MODULE = '0xf2dC2f456b98Af9A6bEEa072AF152a7b0EaA40C9'
ROUTER = '0x68b3465833fb72a70ecdf485e0e4c7bd8665fc45'
SEL_TAKE = '0xbf8d1ddd'  # cast sig take(address,address,address,address,address,bytes,uint256,uint256)
REDEEM_TOPIC = '0x54f4ed50e49638053e1655b45ee7ece434edd150e6771ac0aaedb8355be13a33'
# Flash loan, payout and profit guard are all in native USDC (0x3c49...3359, the farm's Polygon USDC).
# USDC.e is not used anywhere in the route. Amounts named *_usdc below are native USDC, 6 decimals.
PATH = ('0x' + USDC[2:] + '0001f4' + WPOL[2:] + '000bb8' + SWAVE[2:]).lower()
AMOUNT = 25_000_000
POLL_SEC = 30
CU_LIMIT = 95_000
POL_USD_CEILING = 0.20
MAX_SEND_USD = 0.95
MAX_GAS = 3_000_000
MAX_FEE_WEI = 1_000_000_000_000
TIP_WEI = 30_000_000_000
LOG = HERE / 'logs/bot.jsonl'
STATE = HERE / 'state/cu.json'
CU_COST = {'eth_call': 26, 'eth_estimateGas': 20, 'eth_getBlockByNumber': 20,
           'eth_getTransactionReceipt': 20, 'eth_getLogs': 75}
quiet = 0


class ReadBudgetExceeded(Exception):
    pass


def log(ev, **data):
    LOG.parent.mkdir(exist_ok=True)
    with LOG.open('a') as f:
        f.write(json.dumps({'ts': round(time.time(), 3), 'ev': ev, **data}, separators=(',', ':')) + '\n')


def rpc(method, params):
    day = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    try:
        budget = json.loads(STATE.read_text())
    except Exception:
        budget = {'day': day, 'cu': 0}
    if budget.get('day') != day:
        budget = {'day': day, 'cu': 0}
    budget['cu'] += CU_COST.get(method, 26)
    if budget['cu'] > CU_LIMIT:
        raise ReadBudgetExceeded(f'{CU_LIMIT} CU/day cap')
    STATE.parent.mkdir(exist_ok=True)
    STATE.write_text(json.dumps(budget))
    body = json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params}).encode()
    req = urllib.request.Request(f'{RELAY}/{CHAIN}?lane={LANE}', body, {'content-type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            ans = json.load(resp)
    except urllib.error.HTTPError as e:
        if e.code == 429:
            raise ReadBudgetExceeded('relay HTTP 429') from e
        raise
    if 'error' in ans:
        if any(s in str(ans['error']).lower() for s in ('cu cap', 'quota', 'budget exceeded', 'rate limit')):
            raise ReadBudgetExceeded(str(ans['error'])[:160])
        raise RuntimeError(f'{method}: {str(ans["error"])[:240]}')
    return ans['result']


def w(n):
    return format(n, '064x')


def a(addr):
    return addr.lower().removeprefix('0x').zfill(64)


def owner():
    if MODE == 'paper':
        return OWNER_PAPER
    import farmbot_signer
    result = farmbot_signer.my_address()
    address = result['address'] if isinstance(result, dict) else result
    if not isinstance(address, str) or len(address) != 42:
        raise RuntimeError('signer my_address returned no address')
    return address


def executor():
    return EXEC_LIVE if MODE == 'live' else EXEC_PAPER


def calldata(min_profit):
    raw = PATH[2:]
    return (SEL_TAKE + a(MORPHO) + a(USDC) + a(SWAVE) + a(MODULE) + a(ROUTER)
            + w(8 * 32) + w(AMOUNT) + w(min_profit) + w(len(raw)//2)
            + raw + '00' * ((-len(raw)//2) % 32))


def call_params(min_profit, gas=None):
    ex = executor()
    tx = {'from': owner(), 'to': ex, 'data': calldata(min_profit)}
    if gas is not None:
        tx['gas'] = hex(gas)
    params = [tx, 'latest']
    if MODE == 'paper':
        params.append({ex: {'code': RUNTIME.read_text().strip()}})
    return params


def gain(min_profit, gas=None, log_revert=False):
    try:
        return int(rpc('eth_call', call_params(min_profit, gas)), 16)
    except ReadBudgetExceeded:
        raise
    except Exception as e:
        if log_revert:
            log('simulate_revert', min_profit=min_profit, error=str(e)[:200])
        return 0


def winner_block(block):
    filt = {'address': MODULE, 'topics': [REDEEM_TOPIC, '0x'+a(SWAVE)],
            'fromBlock': hex(max(0, block-60)), 'toBlock': hex(block+2)}
    logs = rpc('eth_getLogs', [filt])
    return max((int(x['blockNumber'], 16) for x in logs), default=None)


def send_live(gross, cap_usdc, gas_limit, max_fee):
    import farmbot_signer
    reply = farmbot_signer.send(CHAIN, EXEC_LIVE, calldata(cap_usdc), 0,
                                gas_limit, max_fee, max_priority_fee_per_gas=TIP_WEI)
    txh = reply.get('txHash') if isinstance(reply, dict) else None
    if not txh:
        log('signer_reject', reply=reply)
        return
    rc = None
    for _ in range(20):
        time.sleep(1.5)
        rc = rpc('eth_getTransactionReceipt', [txh])
        if rc:
            break
    if not rc:
        log('send_result', hash=txh, result='unknown', expected_gross_usdc=gross,
            cap_usdc=cap_usdc, gas_limit=gas_limit, winner_block=None)
        return
    block = int(rc['blockNumber'], 16)
    won = int(rc['status'], 16) == 1
    used = int(rc['gasUsed'], 16)
    fee = int(rc['effectiveGasPrice'], 16)
    try:
        winner = block if won else winner_block(block)
    except Exception as e:
        log('winner_lookup_error', hash=txh, error=str(e)[:160])
        winner = None
    log('send_result', hash=txh, result='won' if won else 'lost', gas_used=used,
        gas_cost_pol=used*fee/1e18, gas_limit=gas_limit, max_fee_wei=max_fee,
        expected_gross_usdc=gross, cap_usdc=cap_usdc, send_block=block,
        winner_block=winner, tx_index=int(rc['transactionIndex'], 16))


def check():
    global quiet
    gross = gain(1)
    if gross < 50_000:  # at least five cents of gross before a gas estimate
        quiet += 1
        if quiet % 20 == 1:
            log('check', result='below_interest', best_usdc=gross)
        return
    quiet = 0
    base = int(rpc('eth_getBlockByNumber', ['latest', False])['baseFeePerGas'], 16)
    max_fee = base * 5 // 4 + TIP_WEI
    if max_fee > MAX_FEE_WEI:
        log('opportunity_skip', reason='fee_ceiling', gross_usdc=gross, max_fee_wei=max_fee)
        return
    try:
        estimate = int(rpc('eth_estimateGas', call_params(1)), 16)
    except Exception as e:
        log('simulate_revert', step='estimate', error=str(e)[:200])
        return
    gas_limit = estimate * 115 // 100
    cap_usdc = (gas_limit * max_fee * POL_USD_CEILING * 1e6 / 1e18)
    cap_usdc = int(cap_usdc) + 1
    log('opportunity', gross_usdc=gross, cap_usdc=cap_usdc, gas_estimate=estimate,
        gas_limit=gas_limit, max_fee_wei=max_fee)
    if gas_limit > MAX_GAS or cap_usdc >= int(MAX_SEND_USD*1e6) or cap_usdc*2 >= gross:
        log('opportunity_skip', reason='gas_or_bid_cap', gross_usdc=gross, cap_usdc=cap_usdc,
            gas_limit=gas_limit)
        return
    checked = gain(cap_usdc, gas_limit, log_revert=True)
    if checked <= cap_usdc:
        log('simulate_revert', step='profit_guard', gross_usdc=gross, cap_usdc=cap_usdc)
        return
    if MODE == 'paper':
        log('paper_sim', result='success', gross_usdc=checked, cap_usdc=cap_usdc,
            gas_estimate=estimate, gas_limit=gas_limit, max_fee_wei=max_fee)
    else:
        send_live(checked, cap_usdc, gas_limit, max_fee)


def main():
    if MODE == 'paper' and not RUNTIME.exists():
        raise SystemExit('missing executor-runtime.hex')
    log('start', mode=MODE, executor=executor(), poll_seconds=POLL_SEC)
    while True:
        start = time.monotonic()
        try:
            check()
        except ReadBudgetExceeded as e:
            log('read_budget', error=str(e))
            now = datetime.datetime.now(datetime.timezone.utc)
            tomorrow = (now + datetime.timedelta(days=1)).date()
            wake = datetime.datetime.combine(tomorrow, datetime.time(), datetime.timezone.utc)
            time.sleep(max(1, (wake-now).total_seconds()))
        except Exception as e:
            log('check_error', error=str(e)[:300])
        time.sleep(max(1, POLL_SEC - (time.monotonic()-start)))


if __name__ == '__main__':
    main()
