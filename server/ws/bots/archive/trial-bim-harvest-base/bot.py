#!/usr/bin/env python3
"""Timed, gas-capped trial of one public BIM Yield harvest on Base."""
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
STRATEGY = '0xBFeF6e2FE9E866Ddc0E7929ddb6CFB6E15313Bd3'  # explorer verified StrategyAeroGaugeV2 clone
WETH = '0x4200000000000000000000000000000000000006'     # strategy.native() verified
PAPER_EXEC = '0xb464f7314d55ec6a9a0cf6f7f6df17af8ed5b352'
PAPER_OWNER = '0xc0ffee0000000000000000000000000000000252'
EXEC = os.environ.get('EXECUTOR_ADDR_BASE') or os.environ.get('EXECUTOR_ADDR')
if MODE == 'live' and not EXEC:
    raise SystemExit('EXECUTOR_ADDR_BASE or EXECUTOR_ADDR required in live mode')
RUNTIME = (HERE / 'executor-runtime.hex').read_text().strip()
if not RUNTIME.startswith('0x') or len(RUNTIME) < 100:
    raise SystemExit('missing paper executor runtime')

SEL_REWARD = '0x97fd323d'  # cast sig callReward()
SEL_TAKE = '0x0b0d9c09'    # cast sig take(address,address,uint256)
T_HARVEST = '0x9bc239f1724cacfb88cb1d66a2dc437467699b68a8c90d7b63110cf4b6f92410'
T_WITHDRAW = '0x7fcf532c15f0a6db0bd6d0e038bea71d30d808c7d98cb3bf7268a95bf5081b65'
# Gas limit = eth_estimateGas x 1.10 at send time. The strategy's swap has a gas-reserve check
# (InsufficientGasForCall), so the limit must sit well above gasUsed: review 2026-11-18 measured
# estimate 1,615,441 vs gasUsed 1,444,778 at block 59,118,153, where a fixed 1.6m limit reverted.
GAS_MARGIN_NUM, GAS_MARGIN_DEN = 11, 10
GAS_LIMIT_MAX = 2_400_000   # refuse to sign above this (estimates at 8 harvests: 1.49m-1.70m)
ROUGH_GAS = 1_500_000       # only for the cheap pre-filter before an estimate is made
BASE_FEE_HEADROOM_PCT = 3   # base fee moved at most 1.6% in 5 s over 1,024 blocks before a harvest
TIP_WEI = 100_000           # 0.0001 gwei, about the 5th percentile tip of included Base txs
MAX_FEE_WEI = 10_000_000   # 0.010 gwei: stop if the current base fee rises above this
L1_ALLOWANCE_WEI = 100_000_000_000  # >3x the largest of seven historical L1 fees (27.3e9 wei)
ETH_REF_USD = 4000.0       # intentionally conservative for the <=1 USD trial cap
MAX_TX_USD = 0.90
POLL_SECONDS = 120         # only within the daily 14:15-15:10 UTC window
CU_CAP = 20_000
CU_COST = {'eth_call': 26, 'eth_getBlockByNumber': 20, 'eth_estimateGas': 20, 'eth_getLogs': 75,
           'eth_getTransactionReceipt': 20, 'eth_blockNumber': 10}

LOG = HERE / 'logs' / 'bot.jsonl'
STATE = HERE / 'state' / 'cu.json'
LOG.parent.mkdir(exist_ok=True)
STATE.parent.mkdir(exist_ok=True)

class ReadBudgetExceeded(Exception):
    pass

def log(event, **fields):
    with LOG.open('a') as f:
        f.write(json.dumps({'ts':round(time.time(),3),'ev':event,**fields},separators=(',',':'))+'\n')

def rpc(method, params):
    day = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    try:
        budget = json.loads(STATE.read_text())
    except Exception:
        budget = {'day':day,'cu':0}
    if budget.get('day') != day:
        budget = {'day':day,'cu':0}
    budget['cu'] += CU_COST.get(method,26)
    if budget['cu'] > CU_CAP:
        raise ReadBudgetExceeded(f'{CU_CAP} CU/day cap')
    STATE.write_text(json.dumps(budget))
    body = json.dumps({'jsonrpc':'2.0','id':1,'method':method,'params':params}).encode()
    req = urllib.request.Request(f'{RELAY}/{CHAIN}?lane={LANE}',body,{'content-type':'application/json'})
    with urllib.request.urlopen(req,timeout=30) as resp:
        ans = json.load(resp)
    if 'error' in ans:
        raise RuntimeError(f'{method}: {str(ans["error"])[:240]}')
    return ans['result']

def word(n):
    return format(n,'064x')

def aw(addr):
    return addr.lower().removeprefix('0x').zfill(64)

def calldata(min_profit):
    return SEL_TAKE + aw(STRATEGY) + aw(WETH) + word(min_profit)

def owner():
    import farmbot_signer
    result = farmbot_signer.my_address()
    address = result['address'] if isinstance(result,dict) else result
    if not isinstance(address,str) or len(address) != 42:
        raise RuntimeError('signer my_address returned no address')
    return address

def call_params(min_profit, gas_limit=None):
    address = EXEC if MODE == 'live' else PAPER_EXEC
    tx = {'from':owner() if MODE == 'live' else PAPER_OWNER,
          'to':address,'data':calldata(min_profit)}
    if gas_limit is not None:
        tx['gas'] = hex(gas_limit)
    params = [tx,'latest']
    if MODE == 'paper':
        params.append({address:{'code':RUNTIME}})
    return params

def estimate_limit():
    """Smallest gas limit the node accepts for take(...,1), plus the margin."""
    estimate = int(rpc('eth_estimateGas',call_params(1)),16)
    return estimate, estimate*GAS_MARGIN_NUM//GAS_MARGIN_DEN

def simulate(min_profit, gas_limit):
    """eth_call with exactly the gas limit that would be signed."""
    return int(rpc('eth_call',call_params(min_profit,gas_limit)),16)

def winner_block(block, tx_hash):
    # A failed call usually means the incumbent harvested just before us.
    latest = int(rpc('eth_blockNumber',[]),16)
    logs = rpc('eth_getLogs',[{'address':STRATEGY,
        'fromBlock':hex(max(0,block-100)), 'toBlock':hex(max(block,latest)),
        'topics':[T_HARVEST]}])
    ours = [int(x['blockNumber'],16) for x in logs if x['transactionHash'].lower()==tx_hash.lower()]
    if ours: return min(ours)
    rivals = [int(x['blockNumber'],16) for x in logs if int(x['blockNumber'],16)<=block]
    return max(rivals,default=None)

def send_live(gross, cap, max_fee, min_profit, gas_limit):
    import farmbot_signer
    # The signer turns a tip of 0 into maxFee/10, so the tip is always passed explicitly.
    reply = farmbot_signer.send(CHAIN,EXEC,calldata(min_profit),0,gas_limit,
                                max_fee,max_priority_fee_per_gas=TIP_WEI)
    tx_hash = reply.get('txHash') if isinstance(reply,dict) else None
    if not tx_hash:
        log('signer_reject',reply=reply)
        return
    receipt = None
    for _ in range(30):
        time.sleep(0.5)
        receipt = rpc('eth_getTransactionReceipt',[tx_hash])
        if receipt: break
    if not receipt:
        log('send_result',hash=tx_hash,result='unknown',gross_wei=gross,cap_wei=cap,
            gas_limit=gas_limit,max_fee_wei=max_fee,gas_used=None,winner_block=None)
        return
    block = int(receipt['blockNumber'],16)
    status = int(receipt['status'],16)
    used = int(receipt['gasUsed'],16)
    cost = used*int(receipt['effectiveGasPrice'],16)+int(receipt.get('l1Fee') or '0x0',16)
    paid = sum(int(e['data'],16) for e in receipt.get('logs',[])
               if e['address'].lower()==WETH.lower() and e['topics']
               and e['topics'][0].lower()==T_WITHDRAW and len(e['topics'])>1
               and e['topics'][1][-40:].lower()==EXEC[-40:].lower()) if status else 0
    try: winner = winner_block(block,tx_hash)
    except Exception as e:
        log('winner_lookup_error',hash=tx_hash,error=str(e)[:160])
        winner = None
    log('send_result',hash=tx_hash,result='won' if status else 'lost',
        gas_used=used,gas_limit=gas_limit,max_fee_wei=max_fee,cap_wei=cap,
        gas_cost_wei=cost,expected_gross_wei=gross,paid_wei=paid,
        net_wei=paid-cost if status else -cost,
        send_block=block,winner_block=winner,
        blocks_after_winner=block-winner if winner is not None else None)

def check():
    quote = int(rpc('eth_call',[{'to':STRATEGY,'data':SEL_REWARD},'latest']),16)
    base_fee = int(rpc('eth_getBlockByNumber',['latest',False])['baseFeePerGas'],16)
    # maxFeePerGas = latest base fee + headroom + the fixed tip: the most a unit of gas can cost.
    max_fee = base_fee+base_fee*BASE_FEE_HEADROOM_PCT//100+TIP_WEI
    if max_fee > MAX_FEE_WEI:
        log('opportunity_skip',reason='fee_cap',quote_wei=quote,base_fee=base_fee,max_fee_wei=max_fee)
        return
    rough_cap = ROUGH_GAS*max_fee+L1_ALLOWANCE_WEI
    if quote <= rough_cap*9//10:
        log('check',quote_wei=quote,cap_wei=rough_cap,base_fee=base_fee,reason='reward_below_threshold')
        return
    try:
        estimate, gas_limit = estimate_limit()
    except Exception as e:
        log('simulate_revert',step='estimate',quote_wei=quote,error=str(e)[:200])
        return
    cap = gas_limit*max_fee+L1_ALLOWANCE_WEI
    cap_usd = cap/1e18*ETH_REF_USD
    if gas_limit > GAS_LIMIT_MAX or cap_usd >= MAX_TX_USD:
        log('opportunity_skip',reason='gas_limit_or_usd_cap',quote_wei=quote,gas_estimate=estimate,
            gas_limit=gas_limit,cap_wei=cap,cap_usd=cap_usd)
        return
    try:
        gross = simulate(1,gas_limit)
    except Exception as e:
        log('simulate_revert',quote_wei=quote,cap_wei=cap,gas_limit=gas_limit,error=str(e)[:200])
        return
    log('opportunity',quote_wei=quote,gross_wei=gross,cap_wei=cap,base_fee=base_fee,
        max_fee_wei=max_fee,tip_wei=TIP_WEI,gas_estimate=estimate,gas_limit=gas_limit)
    if gross <= cap:
        log('opportunity_skip',reason='gross_not_above_signed_gas_cap',gross_wei=gross,cap_wei=cap,
            gas_limit=gas_limit)
        return
    min_profit = cap+1
    try:
        checked = simulate(min_profit,gas_limit)
    except Exception as e:
        log('simulate_revert',gross_wei=gross,cap_wei=cap,gas_limit=gas_limit,error=str(e)[:200])
        return
    if checked <= cap:
        log('opportunity_skip',reason='guard_sim_below_cap',gross_wei=checked,cap_wei=cap)
        return
    if MODE == 'paper':
        log('paper_sim',result='success',gross_wei=checked,cap_wei=cap,gas_estimate=estimate,
            gas_limit=gas_limit,max_fee_wei=max_fee,tip_wei=TIP_WEI)
    else:
        send_live(checked,cap,max_fee,min_profit,gas_limit)

def main():
    log('start',mode=MODE,executor=EXEC if MODE=='live' else PAPER_EXEC,
        strategy=STRATEGY,poll_seconds=POLL_SECONDS)
    while True:
        started = time.monotonic()
        try:
            check()
        except ReadBudgetExceeded as e:
            log('read_budget',error=str(e))
            time.sleep(3600)
        except Exception as e:
            log('check_error',error=str(e)[:300])
        now = datetime.datetime.now(datetime.timezone.utc)
        window_start = now.replace(hour=14,minute=15,second=0,microsecond=0)
        window_end = now.replace(hour=15,minute=10,second=0,microsecond=0)
        if window_start <= now < window_end:
            delay = max(1,POLL_SECONDS-(time.monotonic()-started))
        else:
            if now >= window_end:
                window_start += datetime.timedelta(days=1)
            delay = max(1,(window_start-now).total_seconds())
        log('next_check',delay_seconds=round(delay,1))
        time.sleep(delay)

if __name__ == '__main__':
    main()
