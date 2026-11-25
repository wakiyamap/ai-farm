#!/usr/bin/env python3
"""trial: public harvest(token) of the Lester Labs launchpad migrator on Base, caller tip sold to ETH in one tx."""
import sys
sys.path.append('/opt/farm/lib')
import datetime
import json
import os
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
MODE = os.environ.get('BOT_MODE', 'paper')
RELAY = os.environ['RPC_RELAY_URL'].rstrip('/')
LANE = os.environ.get('RPC_LANE', 'paper')
CHAIN = 'base'
# explorer-verified (blockscout) UniV2Migrator; launchpad() answers 0x23231924281b34bb28f10d854db8d2dcbd7f78c5
MIGRATOR = '0x60070f76f885616d675305624497ed0797303434'
CBLTC = '0xcb17c9db87b595717c857a08468793f5bab6445f'   # pairAsset(token) of both coins, 8 decimals
POOL = '0x200681425b0c8d78c6a467512c5d49fa56bac88a'    # Aerodrome CL WETH (token0) / cbLTC (token1), the pool the incumbent sells on
WETH = '0x4200000000000000000000000000000000000006'
# the two coins with a Harvested log in the 7 days to 2026-11-22 (122 logs, no other coin)
TOKENS = {
    'LESTER': '0x319a4924f6660a0660845418fa754a7684c19200',
    'NOTUS': '0x4cfcdd76df7f00f7f7d911263947a9b5ed0b0fe5',
}
PAPER_EXEC = '0xb464f7314d55ec6a9a0cf6f7f6df17af8ed5b352'   # fork deployment (proof.py); paper code override only
PAPER_OWNER = '0xc0ffee0000000000000000000000000000000377'
EXEC = os.environ.get('EXECUTOR_ADDR_BASE') or os.environ.get('EXECUTOR_ADDR')
if MODE == 'live' and not EXEC:
    raise SystemExit('EXECUTOR_ADDR_BASE or EXECUTOR_ADDR required in live mode')
RUNTIME = (HERE / 'executor-runtime.hex').read_text().strip()
if not RUNTIME.startswith('0x') or len(RUNTIME) < 100:
    raise SystemExit('missing paper executor runtime')

SEL_TAKE = '0xbca96701'   # cast sig take(address,address,address,address,address,uint256)
T_HARVESTED = '0x28664d93e9026fea84452d6d4000ed374e5a06781feffd2f9b3300470f2fa9d1'  # cast keccak Harvested(address,address,uint256,uint256,uint256,uint256,address,uint256)
T_WITHDRAWAL = '0x7fcf532c15f0a6db0bd6d0e038bea71d30d808c7d98cb3bf7268a95bf5081b65'  # WETH Withdrawal(address,uint256)
ERRORS = {'0x2edd9b49': 'HarvestCooldown', '0x05d7702d': 'NothingToSell', '0xe39aafee': 'NoProfit'}

POLL_SECONDS = 120          # tips grow over tens of minutes (median 86 min between harvests of one coin)
COOLDOWN_SECONDS = 300      # the migrator's HARVEST_COOLDOWN: no second look at a coin we just took
GAS_MARGIN_NUM, GAS_MARGIN_DEN = 12, 10
GAS_LIMIT_MAX = 900_000     # takes measured 388k-590k gas (24 receipts); fork success 527,728
PRIORITY_WEI = 2_500_000    # 0.0025 gwei: just above the rivals' usual 0.002 gwei; fixed, never raised
BASE_FEE_HEADROOM_PCT = 25
MAX_FEE_WEI = 50_000_000    # 0.05 gwei: do nothing while the base fee is above this
L1_ALLOWANCE_WEI = 300_000_000_000   # over 2 x the largest L1 fee of 24 rival takes (1.28e11 wei)
GROSS_OVER_CAP = 1.5        # send only when the simulated gain is at least 1.5 x the signed gas cap
ETH_REF_USD = 4000.0        # conservative price for the 1 USD per send limit
MAX_TX_USD = 0.90
CU_CAP = 60_000
CU_COST = {'eth_call': 26, 'eth_getBlockByNumber': 20, 'eth_estimateGas': 20, 'eth_getLogs': 75,
           'eth_getTransactionReceipt': 20, 'eth_blockNumber': 10}

LOG = HERE / 'logs' / 'bot.jsonl'
STATE = HERE / 'state' / 'cu.json'
LOG.parent.mkdir(exist_ok=True)
STATE.parent.mkdir(exist_ok=True)


class ReadBudgetExceeded(Exception):
    pass


class CallReverted(Exception):
    def __init__(self, data, message):
        super().__init__(message)
        self.data = data


def log(event, **fields):
    with LOG.open('a') as f:
        f.write(json.dumps({'ts': round(time.time(), 3), 'ev': event, **fields}, separators=(',', ':')) + '\n')


def rpc(method, params):
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
    STATE.write_text(json.dumps(budget))
    body = json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params}).encode()
    req = urllib.request.Request(f'{RELAY}/{CHAIN}?lane={LANE}', body, {'content-type': 'application/json'})
    with urllib.request.urlopen(req, timeout=30) as resp:
        ans = json.load(resp)
    if 'error' in ans:
        err = ans['error']
        data = err.get('data') if isinstance(err, dict) else None
        if isinstance(data, str) and data.startswith('0x'):
            raise CallReverted(data[:10], f'{method}: {str(err)[:200]}')
        raise RuntimeError(f'{method}: {str(err)[:240]}')
    return ans['result']


def word(n):
    return format(n, '064x')


def aw(addr):
    return addr.lower().removeprefix('0x').zfill(64)


def calldata(token, min_profit):
    return SEL_TAKE + aw(MIGRATOR) + aw(token) + aw(CBLTC) + aw(POOL) + aw(WETH) + word(min_profit)


def owner():
    import farmbot_signer
    result = farmbot_signer.my_address()
    address = result['address'] if isinstance(result, dict) else result
    if not isinstance(address, str) or len(address) != 42:
        raise RuntimeError('signer my_address returned no address')
    return address


def call_params(token, min_profit, gas_limit=None):
    address = EXEC if MODE == 'live' else PAPER_EXEC
    tx = {'from': owner() if MODE == 'live' else PAPER_OWNER, 'to': address, 'data': calldata(token, min_profit)}
    if gas_limit is not None:
        tx['gas'] = hex(gas_limit)
    params = [tx, 'latest']
    if MODE == 'paper':
        params.append({address: {'code': RUNTIME}})
    return params


def simulate(token, min_profit, gas_limit=None):
    """take() as an eth_call: the native wei that would reach the wallet, or CallReverted."""
    return int(rpc('eth_call', call_params(token, min_profit, gas_limit)), 16)


def winner_block(token, block, tx_hash):
    latest = int(rpc('eth_blockNumber', []), 16)
    logs = rpc('eth_getLogs', [{'address': MIGRATOR, 'fromBlock': hex(max(0, block - 1500)), 'toBlock': hex(max(block, latest)),
                                'topics': [T_HARVESTED, '0x' + aw(token)]}])
    ours = [int(x['blockNumber'], 16) for x in logs if x['transactionHash'].lower() == tx_hash.lower()]
    if ours:
        return min(ours)
    rivals = [int(x['blockNumber'], 16) for x in logs if int(x['blockNumber'], 16) <= block]
    return max(rivals, default=None)


def send_live(name, token, gross, cap, max_fee, min_profit, gas_limit):
    import farmbot_signer
    reply = farmbot_signer.send(CHAIN, EXEC, calldata(token, min_profit), 0, gas_limit,
                                max_fee, max_priority_fee_per_gas=PRIORITY_WEI)
    tx_hash = reply.get('txHash') if isinstance(reply, dict) else None
    if not tx_hash:
        log('signer_reject', coin=name, reply=reply)
        return
    log('send', coin=name, hash=tx_hash, expected_gross_wei=gross, cap_wei=cap, gas_limit=gas_limit,
        max_fee_wei=max_fee, priority_wei=PRIORITY_WEI, min_profit_wei=min_profit)
    receipt = None
    for _ in range(30):
        time.sleep(0.5)
        receipt = rpc('eth_getTransactionReceipt', [tx_hash])
        if receipt:
            break
    if not receipt:
        log('send_result', coin=name, hash=tx_hash, result='unknown', expected_gross_wei=gross, cap_wei=cap,
            gas_limit=gas_limit, max_fee_wei=max_fee, gas_used=None, winner_block=None)
        return
    block = int(receipt['blockNumber'], 16)
    status = int(receipt['status'], 16)
    used = int(receipt['gasUsed'], 16)
    cost = used * int(receipt['effectiveGasPrice'], 16) + int(receipt.get('l1Fee') or '0x0', 16)
    # what the executor unwrapped = what it paid the wallet (WETH Withdrawal logs of the executor)
    paid = sum(int(e['data'], 16) for e in receipt.get('logs', [])
               if e['address'].lower() == WETH.lower() and e['topics']
               and e['topics'][0].lower() == T_WITHDRAWAL and len(e['topics']) > 1
               and e['topics'][1][-40:].lower() == EXEC[-40:].lower()) if status else 0
    try:
        winner = winner_block(token, block, tx_hash)
    except Exception as e:
        log('winner_lookup_error', hash=tx_hash, error=str(e)[:160])
        winner = None
    log('send_result', coin=name, hash=tx_hash, result='won' if status else 'lost', gas_used=used, gas_limit=gas_limit,
        max_fee_wei=max_fee, cap_wei=cap, gas_cost_wei=cost, expected_gross_wei=gross, paid_wei=paid,
        net_wei=(paid - cost) if status else -cost, send_block=block, winner_block=winner,
        blocks_after_winner=block - winner if winner is not None else None)


def check(name, token):
    """Returns True when the coin was taken (or paper-taken) and should rest for the cooldown."""
    try:
        gross = simulate(token, 1)
    except CallReverted as e:
        log('check', coin=name, gross_wei=0, reason=ERRORS.get(e.data, e.data))
        return False
    # cheap pre-filter before the fee reads: below the cost of 300k gas at the floor base fee nothing can pass
    if gross < 3_000_000_000_000:
        log('check', coin=name, gross_wei=gross, reason='tip_below_prefilter')
        return False
    base_fee = int(rpc('eth_getBlockByNumber', ['latest', False])['baseFeePerGas'], 16)
    max_fee = base_fee + base_fee * BASE_FEE_HEADROOM_PCT // 100 + PRIORITY_WEI
    if max_fee > MAX_FEE_WEI:
        log('opportunity_skip', coin=name, reason='fee_cap', gross_wei=gross, base_fee=base_fee, max_fee_wei=max_fee)
        return False
    try:
        estimate = int(rpc('eth_estimateGas', call_params(token, 1)), 16)
    except Exception as e:
        log('simulate_revert', coin=name, step='estimate', gross_wei=gross, error=str(e)[:200])
        return False
    gas_limit = estimate * GAS_MARGIN_NUM // GAS_MARGIN_DEN
    cap = gas_limit * max_fee + L1_ALLOWANCE_WEI      # the most this send can cost
    cap_usd = cap / 1e18 * ETH_REF_USD
    if gas_limit > GAS_LIMIT_MAX or cap_usd >= MAX_TX_USD:
        log('opportunity_skip', coin=name, reason='gas_limit_or_usd_cap', gross_wei=gross, gas_estimate=estimate,
            gas_limit=gas_limit, cap_wei=cap, cap_usd=cap_usd)
        return False
    log('opportunity', coin=name, gross_wei=gross, cap_wei=cap, base_fee=base_fee, max_fee_wei=max_fee,
        priority_wei=PRIORITY_WEI, gas_estimate=estimate, gas_limit=gas_limit)
    if gross < GROSS_OVER_CAP * cap:
        log('opportunity_skip', coin=name, reason='gross_below_1.5x_gas_cap', gross_wei=gross, cap_wei=cap)
        return False
    min_profit = cap + 1     # the executor reverts unless more than the gas cap reaches the wallet
    try:
        checked = simulate(token, min_profit, gas_limit)
    except Exception as e:
        log('simulate_revert', coin=name, step='guard', gross_wei=gross, cap_wei=cap, gas_limit=gas_limit, error=str(e)[:200])
        return False
    if checked <= cap:
        log('opportunity_skip', coin=name, reason='guard_sim_below_cap', gross_wei=checked, cap_wei=cap)
        return False
    if MODE == 'paper':
        log('paper_sim', coin=name, result='success', gross_wei=checked, cap_wei=cap, net_floor_wei=checked - cap,
            gas_estimate=estimate, gas_limit=gas_limit, max_fee_wei=max_fee, priority_wei=PRIORITY_WEI)
    else:
        send_live(name, token, checked, cap, max_fee, min_profit, gas_limit)
    return True


def main():
    log('start', mode=MODE, executor=EXEC if MODE == 'live' else PAPER_EXEC, migrator=MIGRATOR,
        coins=list(TOKENS), poll_seconds=POLL_SECONDS)
    rest_until = {}
    while True:
        started = time.monotonic()
        delay = POLL_SECONDS
        try:
            for name, token in TOKENS.items():
                if time.time() < rest_until.get(name, 0):
                    continue
                if check(name, token):
                    rest_until[name] = time.time() + COOLDOWN_SECONDS
        except ReadBudgetExceeded as e:
            now = datetime.datetime.now(datetime.timezone.utc)
            midnight = (now + datetime.timedelta(days=1)).replace(hour=0, minute=0, second=5, microsecond=0)
            delay = max(60, (midnight - now).total_seconds())
            log('read_budget', error=str(e), sleep_seconds=round(delay))
        except Exception as e:
            log('check_error', error=str(e)[:300])
        time.sleep(max(1, delay - (time.monotonic() - started)))


if __name__ == '__main__':
    main()
