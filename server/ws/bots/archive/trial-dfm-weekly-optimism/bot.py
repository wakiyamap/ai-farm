#!/usr/bin/env python3
"""trial: defi.money weekly fee distribution on OP Mainnet. PrimaryFeeAggregator.processWeeklyDistribution() is
unguarded, can run once per protocol week (weeks start Sunday 12:00:00 UTC) and pays its caller `callerIncentive`
(10 MONEY) when the aggregator holds more than twice that. One transaction through the WeeklyCaller executor does:
PegKeeperRegulator.withdraw_profit() and FeeConverter.transferToAggregator() (both public, they move accrued fees
to the aggregator; a failing one is skipped) -> processWeeklyDistribution() -> the 10 MONEY sold for USDC on the
Curve USDC / MONEY pool -> USDC to the bot wallet, and reverts unless the USDC gained is at least minProfit.
Timer bot: it sleeps to the next week start, then simulates the exact transaction once a second for two minutes;
if the week stays undistributed (nothing to distribute yet) it looks again every 10 minutes."""
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
CHAIN = 'optimism'

# Addresses (README "Addresses": verified sources on the explorer, each checked with a getter).
AGGREGATOR = '0xfeea66de54c040cf8323bc6f2f83c1ba70aacab9'   # verified PrimaryFeeAggregator
CONVERTER = '0xee84dd92653a66bf342d52aa0913a2eab3b5c2fe'    # verified FeeConverter, transferToAggregator()
REGULATOR = '0xe7e7185c801d28197cbc8d724f67f402d948c0c1'    # PegKeeperRegulator, withdraw_profit()
MONEY = '0x69420f9e38a4e60a62224c489be4bf7a94402496'        # the protocol stablecoin (symbol() MONEY)
USDC = '0x0b2c639c533813f4aa9d7837caf62653d097ff85'         # native USDC on OP Mainnet
POOL = '0x8f63ccd329d4ba07a3c6703d94d3137a9cfbfc6c'         # Curve pool, coins(0) = USDC, coins(1) = MONEY
POOL_I, POOL_J = 1, 0                                       # sell MONEY (1) for USDC (0)
GAS_ORACLE = '0x420000000000000000000000000000000000000F'   # OP Stack GasPriceOracle predeploy, getL1Fee(bytes)

# Selectors and the topic, all from `cast sig` / `cast keccak` (scratch/trial-dfm-weekly-optimism/setup.py).
SEL_RUN = '0xeb0dfdb7'        # run(address[],bytes4[],address,address,address,int128,int128,address,uint256)
SEL_WITHDRAW_PROFIT = '0x2c9f7f92'   # withdraw_profit()
SEL_TO_AGGREGATOR = '0xd09b8eed'     # transferToAggregator()
SEL_LAST_WEEK = '0x43a0c3ca'  # lastDistributionWeek()
SEL_L1_FEE = '0x49948e0e'     # getL1Fee(bytes)
TOPIC_PWD = '0x219812af16ae7b0244f25901385406aeb832e75fe0422c0eb6479e8781fcdf25'   # ProcessWeeklyDistribution(address,uint256,uint256)
PRE = [(REGULATOR, SEL_WITHDRAW_PROFIT), (CONVERTER, SEL_TO_AGGREGATOR)]

# Protocol weeks: week n starts at WEEK0 + n * WEEK. From the chain: lastDistributionWeek() = 126 was written by the
# take at block 159,875,018 (timestamp 1795348813 = Sunday 2026-11-22 12:00:13 UTC), 13 s after 1795348800.
WEEK0 = 1719144000            # Sunday 2024-06-23 12:00:00 UTC
WEEK = 604800

PAPER_EXEC = '0x00000000000000000000000000000000000f11b5'   # code-override address, paper only
PAPER_OWNER = '0xc0ffee0000000000000000000000000000000321'  # owner baked into the fork deployment's runtime code
EXEC = os.environ.get('EXECUTOR_ADDR_OPTIMISM') or os.environ.get('EXECUTOR_ADDR')
if MODE == 'live' and not EXEC:
    raise SystemExit('EXECUTOR_ADDR_OPTIMISM or EXECUTOR_ADDR required in live mode')
RUNTIME_FILE = HERE / 'executor-runtime.hex'

BURST_BEFORE_S = 2                # start looking this long before the week start
BURST_S = 120                     # one look a second for this long after it
SLOW_POLL_S = 600                 # afterwards, while the week is still undistributed
MAX_SENDS_PER_WEEK = 3            # a lost send costs under a cent; never more than this many per week
TIP_WEI = 5_000_000               # 0.005 gwei priority fee, never raised (the 11-22 winner paid about 0.002 gwei in all); under 0.5 pct of gross
MAX_FEE_CAP_WEI = 2 * 10**9       # 2 gwei: never sign above this
GAS_LIMIT_MAX = 2_500_000
ETH_REF_USD = 4000.0              # conservative (about 1,700 USD on 2026-11-22): overstates every gas bound
MAX_TX_USD = 0.95
CU_CAP = 60_000
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


def run_calldata(min_profit):
    """run(address[] preTargets, bytes4[] preSelectors, aggregator, stable, pool, i, j, usdc, minProfit)."""
    n = len(PRE)
    targets = w(n) + ''.join(a(t) for t, _ in PRE)
    sels = w(n) + ''.join(s.removeprefix('0x').ljust(64, '0') for _, s in PRE)
    head = 9 * 32
    return (SEL_RUN + w(head) + w(head + len(targets) // 2) + a(AGGREGATOR) + a(MONEY) + a(POOL)
            + w(POOL_I) + w(POOL_J) + a(USDC) + w(min_profit) + targets + sels)


def owner():
    import farmbot_signer
    result = farmbot_signer.my_address()
    address = result['address'] if isinstance(result, dict) else result
    if not isinstance(address, str) or len(address) != 42:
        raise RuntimeError('signer my_address returned no address')
    return address


def executor():
    return EXEC if MODE == 'live' else PAPER_EXEC


def call_params(min_profit, gas_limit=None, block='latest'):
    ex = executor()
    tx = {'from': owner() if MODE == 'live' else PAPER_OWNER, 'to': ex, 'data': run_calldata(min_profit)}
    if gas_limit is not None:
        tx['gas'] = hex(gas_limit)
    params = [tx, block]
    if MODE == 'paper':
        params.append({ex: {'code': RUNTIME_FILE.read_text().strip()}})
    return params


def gain_of(min_profit=1, gas_limit=None, block='latest'):
    """USDC gain (6 decimals) of run() as an eth_call of the exact transaction; 0 when it reverts (week already
    distributed, nothing to distribute, or NoProfit)."""
    ans = rpc('eth_call', call_params(min_profit, gas_limit, block), raw=True)
    if 'error' in ans:
        return 0, str(ans['error'])[:200]
    return int(ans['result'], 16), None


def last_week():
    return int(rpc('eth_call', [{'to': AGGREGATOR, 'data': SEL_LAST_WEEK}, 'latest']), 16)


def week_of(ts):
    return int(ts - WEEK0) // WEEK


def fees():
    base_fee = int(rpc('eth_getBlockByNumber', ['latest', False])['baseFeePerGas'], 16)
    return base_fee, 2 * base_fee + TIP_WEI


def l1_fee_wei(min_profit):
    """OP Stack L1 data fee of this calldata from the GasPriceOracle, doubled (the signed transaction is a little
    longer than its calldata and the L1 fee can move before inclusion)."""
    data = run_calldata(min_profit).removeprefix('0x')
    n = len(data) // 2
    arg = w(32) + w(n) + data + '00' * ((-n) % 32)
    return 2 * int(rpc('eth_call', [{'to': GAS_ORACLE, 'data': SEL_L1_FEE + arg}, 'latest']), 16)


def winner_near(block):
    """Block and caller of the newest ProcessWeeklyDistribution near our send: the winner when we lost."""
    logs = rpc('eth_getLogs', [{'address': AGGREGATOR, 'fromBlock': hex(block - 2000), 'toBlock': hex(block + 20),
                                'topics': [TOPIC_PWD]}])
    if not logs:
        return None, None
    return int(logs[-1]['blockNumber'], 16), '0x' + logs[-1]['topics'][1][26:]


def send_live(gross, min_profit, cap, max_fee, gas_limit):
    import farmbot_signer
    reply = farmbot_signer.send(CHAIN, EXEC, run_calldata(min_profit), 0, gas_limit,
                                max_fee, max_priority_fee_per_gas=TIP_WEI)
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
    if not receipt:
        log('send_result', hash=tx_hash, result='unknown', expected_gross_usdc=gross, cap_wei=cap,
            gas_limit=gas_limit, max_fee_wei=max_fee, gas_used=None, winner_block=None)
        return
    block = int(receipt['blockNumber'], 16)
    status = int(receipt['status'], 16)
    used = int(receipt['gasUsed'], 16)
    cost = used * int(receipt['effectiveGasPrice'], 16) + int(receipt.get('l1Fee', '0x0'), 16)
    winner, winner_caller = block, None
    if not status:
        try:
            winner, winner_caller = winner_near(block)
        except ReadBudgetExceeded:
            raise
        except Exception as e:
            log('winner_lookup_error', hash=tx_hash, error=str(e)[:160])
            winner = None
    log('send_result', hash=tx_hash, result='won' if status else 'lost', gas_used=used, gas_limit=gas_limit,
        max_fee_wei=max_fee, tip_wei=TIP_WEI, cap_wei=cap, gas_cost_wei=cost,
        expected_gross_usdc=gross if status else 0, min_profit_usdc=min_profit, send_block=block,
        winner_block=winner, winner_caller=winner_caller, tx_index=int(receipt['transactionIndex'], 16))


def check(trigger):
    """One look: simulate the exact transaction. Returns 'sent' (live) / 'would_send' (paper) / 'nothing'."""
    gross, err = gain_of(1)
    if not gross:
        log('check', trigger=trigger, result='nothing', error=err)
        return 'nothing'
    base_fee, max_fee = fees()
    if max_fee > MAX_FEE_CAP_WEI:
        log('opportunity_skip', trigger=trigger, reason='fee_cap', gross_usdc=gross, base_fee=base_fee)
        return 'nothing'
    try:
        estimate = int(rpc('eth_estimateGas', call_params(1)), 16)
    except ReadBudgetExceeded:
        raise
    except Exception as e:
        log('simulate_revert', trigger=trigger, step='estimate', gross_usdc=gross, error=str(e)[:200])
        return 'nothing'
    gas_limit = estimate * 13 // 10
    cap = gas_limit * max_fee + l1_fee_wei(1)          # the most this send can cost, wei (L2 bound + L1 data fee)
    cap_usd = cap / 1e18 * ETH_REF_USD
    cap_usdc = int(cap_usd * 1e6) + 1                  # the same in USDC units at the conservative ETH price
    log('opportunity', trigger=trigger, gross_usdc=gross, cap_wei=cap, cap_usdc=cap_usdc, base_fee=base_fee,
        max_fee_wei=max_fee, tip_wei=TIP_WEI, gas_estimate=estimate, gas_limit=gas_limit)
    if gas_limit > GAS_LIMIT_MAX or cap_usd >= MAX_TX_USD:
        log('opportunity_skip', reason='gas_limit_or_usd_cap', gas_limit=gas_limit, cap_usd=cap_usd)
        return 'nothing'
    if gross <= cap_usdc:                              # send only when expected gross > this send's gas cap
        log('opportunity_skip', reason='gross_not_above_gas_cap', gross_usdc=gross, cap_usdc=cap_usdc)
        return 'nothing'
    min_profit = max(cap_usdc, gross // 2)             # the transaction itself reverts below this
    if MODE == 'paper':
        log('paper_sim', result='success', trigger=trigger, gross_usdc=gross, min_profit_usdc=min_profit,
            cap_wei=cap, cap_usdc=cap_usdc, gas_estimate=estimate, gas_limit=gas_limit, max_fee_wei=max_fee,
            tip_wei=TIP_WEI)
        return 'would_send'
    send_live(gross, min_profit, cap, max_fee, gas_limit)
    return 'sent'


def sleep_until(t):
    """Sleep without any read, in chunks, so a clock step is noticed."""
    while True:
        left = t - time.time()
        if left <= 0:
            return
        time.sleep(min(left, 300))


def main():
    """Timer loop. Every relay read is inside the try that catches the bot's CU cap."""
    if MODE == 'paper' and not RUNTIME_FILE.exists():
        raise SystemExit('missing executor-runtime.hex (paper code override)')
    log('start', mode=MODE, executor=executor(), aggregator=AGGREGATOR, pool=POOL,
        next_week_start=WEEK0 + (week_of(time.time()) + 1) * WEEK)
    sends = {}                                         # protocol week -> sends made (live) or simulated (paper)
    while True:
        try:
            now = time.time()
            week = week_of(now)
            start = WEEK0 + week * WEEK
            next_start = start + WEEK
            done = last_week() >= week
            if done or sends.get(week, 0) >= MAX_SENDS_PER_WEEK:
                log('wait', week=week, distributed=done, sends=sends.get(week, 0), next_week_start=next_start)
                sleep_until(next_start - BURST_BEFORE_S)
                # burst: one look a second from just before the week start
                week = week_of(next_start)
                end = next_start + BURST_S
                while time.time() < end and sends.get(week, 0) < MAX_SENDS_PER_WEEK:
                    t0 = time.time()
                    result = check('week_start')
                    if result != 'nothing':
                        sends[week] = sends.get(week, 0) + 1
                        if result == 'would_send':
                            sends[week] = MAX_SENDS_PER_WEEK      # paper: one line per week is enough
                        if last_week() >= week:
                            break
                    time.sleep(max(0.0, 1.0 - (time.time() - t0)))
                continue
            # the week is open and nobody has distributed it yet: fees may still arrive, look every 10 minutes
            result = check('slow_poll')
            if result != 'nothing':
                sends[week] = sends.get(week, 0) + 1
                if result == 'would_send':
                    sends[week] = MAX_SENDS_PER_WEEK
            sleep_until(min(time.time() + SLOW_POLL_S, next_start - BURST_BEFORE_S))
            if time.time() >= next_start - BURST_BEFORE_S - 1:
                sends.setdefault(week, 0)
                sends[week] = MAX_SENDS_PER_WEEK                   # falls into the wait branch -> burst at once
        except ReadBudgetExceeded as e:
            log('read_budget', error=str(e))
            now = datetime.datetime.now(datetime.timezone.utc)
            time.sleep(86400 - (now.hour * 3600 + now.minute * 60 + now.second) + 5)   # to 00:00 UTC
        except Exception as e:
            log('loop_error', error=str(e)[:250])
            time.sleep(15)


if __name__ == '__main__':
    if len(sys.argv) > 2 and sys.argv[1] == '--selftest':
        # one simulated look at a given block (paper override), no loop: python3 bot.py --selftest <block>
        print(json.dumps({'block': int(sys.argv[2]), 'gain': gain_of(1, None, hex(int(sys.argv[2])))}))
    else:
        main()
