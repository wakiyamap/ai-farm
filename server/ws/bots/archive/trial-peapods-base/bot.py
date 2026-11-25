#!/usr/bin/env python3
"""Confirmed-event trial of public Peapods LVF fWETH liquidations on Base."""
import datetime as dt
import json
import os
from pathlib import Path
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

sys.path.append('/opt/farm/lib')
HERE = Path(__file__).resolve().parent
MODE = os.environ.get('BOT_MODE', 'paper')
RELAY = os.environ['RPC_RELAY_URL'].rstrip('/')
LANE = os.environ.get('RPC_LANE', 'paper')
CHAIN = 'base'
PAIR = '0x23574154842bc86cf5bbc5f99376cfa1e2f82497'
WETH = '0x4200000000000000000000000000000000000006'
MORPHO = '0xbbbbbbbbbb9cc5e90e3b3af64bdaf62c37eeffcb'
COLLATERAL = '0x96b81bf4f562a54d9135d6283f4a36775029d890'
STAKED = '0xe401f3958521b725cf1a816aa2ea4c9a0462a4a4'
POD = '0x9dbf562a65590c03e5400854d498844915c25944'
POOL = '0x8444c479777e9662eeec4a301349be26e90c64de'
INDEX_UTILS = '0x490b03c6afe733576cf1f5d2a821cf261b15826d'
TOPIC_LIQ = '0x821de4e13fff1938b3806eb2859b6a5d55111f00dcf286f8a793584228ff36f8'
TOPIC_TRANSFER = '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
TOPIC_WITHDRAW = '0x7fcf532c15f0a6db0bd6d0e038bea71d30d808c7d98cb3bf7268a95bf5081b65'
SEL_RUN = '0xcf18ee7d'  # cast sig run((address,address,address,address,address,address,address,address,address,uint128,uint256,uint256,uint256,uint256,uint256))
SEL_SHARES = '0x4fd422df'  # cast sig userBorrowShares(address)
SEL_TOTAL = '0x8285ef40'  # cast sig totalBorrow()
PAPER_EXEC = '0xb464f7314d55ec6a9a0cf6f7f6df17af8ed5b352'
PAPER_OWNER = '0x004e329ed4c848feb47f5971cf519500000000b0'
EXEC = os.environ.get('EXECUTOR_ADDR_BASE') or os.environ.get('EXECUTOR_ADDR')
if MODE == 'live' and not EXEC:
    raise SystemExit('EXECUTOR_ADDR_BASE or EXECUTOR_ADDR required in live mode')
RUNTIME = (HERE / 'executor-runtime.hex').read_text().strip()
if not RUNTIME.startswith('0x') or len(RUNTIME) < 100:
    raise SystemExit('missing fork executor runtime')

GAS_LIMIT = 3_200_000  # fork success 2,400,224
MAX_FEE_WEI = 50_000_000
PRIORITY_WEI = 1_000_000
L1_ALLOWANCE_WEI = 100_000_000_000  # historical receipt 13.7e9 wei
ETH_REF_USD = 4000.0  # conservative trial cap calculation
MAX_LOAN_WEI = 250_000_000_000_000_000
CU_CAP = 100_000
CU_COST = {'eth_call': 26, 'eth_getTransactionReceipt': 20, 'eth_getLogs': 75,
           'eth_blockNumber': 10, 'eth_gasPrice': 20}
FEED = 'http://127.0.0.1:8546/logs/base'
LOG = HERE / 'logs' / 'bot.jsonl'
STATE = HERE / 'state' / 'watch.json'
LOG.parent.mkdir(exist_ok=True)
STATE.parent.mkdir(exist_ok=True)

def log(event, **kw):
    with LOG.open('a') as f:
        f.write(json.dumps({'ts':round(time.time(),3),'ev':event,**kw},separators=(',',':'))+'\n')

def load_state():
    try: return json.loads(STATE.read_text())
    except Exception: return {'cursor':None,'seen':{},'cu_day':None,'cu':0}

state = load_state()

def save_state():
    STATE.write_text(json.dumps(state,separators=(',',':')))

def rpc(method, params):
    day = dt.datetime.now(dt.timezone.utc).date().isoformat()
    if state.get('cu_day') != day:
        state['cu_day'],state['cu'] = day,0
    state['cu'] += CU_COST.get(method,26)
    save_state()
    if state['cu'] > CU_CAP: raise RuntimeError('read budget exhausted')
    body=json.dumps({'jsonrpc':'2.0','id':1,'method':method,'params':params}).encode()
    req=urllib.request.Request(f'{RELAY}/{CHAIN}?lane={LANE}',body,{'content-type':'application/json'})
    with urllib.request.urlopen(req,timeout=30) as resp: obj=json.load(resp)
    if 'error' in obj: raise RuntimeError(method+' '+str(obj['error'])[:250])
    return obj['result']

def aw(a): return a.lower().removeprefix('0x').zfill(64)
def word(n): return format(int(n),'064x')

def caller():
    if MODE == 'paper': return PAPER_OWNER
    import farmbot_signer
    ans=farmbot_signer.my_address()
    return ans['address']

def calldata(borrower, shares, loan, deadline, swap_out, profit, max_fee):
    addresses=[MORPHO,WETH,PAIR,COLLATERAL,STAKED,POD,POOL,INDEX_UTILS,borrower]
    return SEL_RUN+''.join(aw(a) for a in addresses)+''.join(word(n) for n in
        (shares,loan,deadline,swap_out,profit,max_fee))

def simulate(borrower, shares, loan, deadline, swap_out, profit, max_fee):
    to=EXEC if MODE=='live' else PAPER_EXEC
    tx={'from':caller(),'to':to,'data':calldata(borrower,shares,loan,deadline,swap_out,profit,max_fee),
        'gas':hex(GAS_LIMIT)}
    params=[tx,'latest']
    if MODE=='paper': params.append({to:{'code':RUNTIME}})
    return int(rpc('eth_call',params),16)

def event_details(e):
    data=e['data'][2:]
    vals=[int(data[i:i+64],16) for i in range(0,len(data),64)]
    if len(vals)<3: raise ValueError('short Liquidate event')
    return '0x'+e['topics'][1][-40:],vals[1],vals[2]

def source_out(txhash):
    r=rpc('eth_getTransactionReceipt',[txhash])
    if not r: return 0
    receiver=(r.get('to') or '').lower()
    return sum(int(l['data'],16) for l in r['logs'] if
        l['address'].lower()==PAIR.lower() and len(l['topics'])==3 and
        l['topics'][0].lower()==TOPIC_TRANSFER and
        '0x'+l['topics'][1][-40:].lower()==POOL.lower() and
        '0x'+l['topics'][2][-40:].lower()==receiver)

def user_shares(borrower):
    return int(rpc('eth_call',[{'to':PAIR,'data':SEL_SHARES+aw(borrower)},'latest']),16)

def total_borrow():
    data=rpc('eth_call',[{'to':PAIR,'data':SEL_TOTAL},'latest'])[2:]
    return int(data[:64],16),int(data[64:128],16)

def fee_cap():
    gas_price=int(rpc('eth_gasPrice',[]),16)
    if gas_price>MAX_FEE_WEI: return None
    max_fee=min(MAX_FEE_WEI,max(gas_price*2+PRIORITY_WEI,10_000_000))
    cap=GAS_LIMIT*max_fee+L1_ALLOWANCE_WEI
    if cap/1e18*ETH_REF_USD>=1.0: return None
    return max_fee,cap

def send_live(borrower, shares, loan, deadline, swap_out, gross, cap, max_fee, trigger_block):
    import farmbot_signer
    data=calldata(borrower,shares,loan,deadline,swap_out,cap+1,max_fee)
    ans=farmbot_signer.send(CHAIN,EXEC,data,0,GAS_LIMIT,max_fee,max_priority_fee_per_gas=PRIORITY_WEI)
    txhash=ans.get('txHash') if isinstance(ans,dict) else None
    if not txhash:
        log('signer_reject',reply=ans,borrower=borrower)
        return
    r=None
    for _ in range(40):
        time.sleep(.5)
        r=rpc('eth_getTransactionReceipt',[txhash])
        if r: break
    if not r:
        log('send_result',result='unknown',hash=txhash,gas_used=None,winner_block=None,
            trigger_block=trigger_block,expected_gross_wei=gross)
        return
    block=int(r['blockNumber'],16)
    used=int(r['gasUsed'],16)
    cost=used*int(r['effectiveGasPrice'],16)+int(r.get('l1Fee') or '0x0',16)+int(r.get('operatorFee') or '0x0',16)
    success=int(r['status'],16)==1
    paid=sum(int(l['data'],16) for l in r['logs'] if success and
        l['address'].lower()==WETH.lower() and l['topics'] and
        l['topics'][0].lower()==TOPIC_WITHDRAW and
        '0x'+l['topics'][1][-40:].lower()==EXEC.lower())
    winner=block if success else trigger_block
    log('send_result',result='won' if success else 'lost',hash=txhash,
        gas_used=used,gas_cost_wei=cost,paid_wei=paid,net_wei=paid-cost if success else -cost,
        winner_block=winner,trigger_block=trigger_block,blocks_after_winner=block-winner)

def check(e, source='feed'):
    borrower,prev_shares,prev_repay=event_details(e)
    previous_out=source_out(e['transactionHash'])
    if previous_out<=0:
        log('opportunity_skip',reason='source_no_pool_output',borrower=borrower,source=source)
        return
    remaining=user_shares(borrower)
    if remaining==0:
        log('opportunity_skip',reason='borrower_repaid',borrower=borrower,source=source)
        return
    amount,all_shares=total_borrow()
    capinfo=fee_cap()
    if not capinfo or not all_shares:
        log('opportunity_skip',reason='fee_or_total_borrow',borrower=borrower)
        return
    max_fee,cap=capinfo
    deadline=int(time.time())+90
    for divisor in (1,2,4):
        shares=min(remaining,prev_shares//divisor)
        if shares==0: continue
        loan=(shares*amount//all_shares)*105//100+10**12
        if loan>MAX_LOAN_WEI: continue
        for pct in (99,95,90,80):
            swap_out=max(1,previous_out*shares//prev_shares*pct//100)
            try:
                gross=simulate(borrower,shares,loan,deadline,swap_out,1,max_fee)
            except Exception as err:
                log('simulate_revert',borrower=borrower,shares=shares,pct=pct,error=str(err)[:180])
                continue
            log('opportunity',borrower=borrower,shares=shares,loan_wei=loan,
                swap_out=swap_out,gross_wei=gross,gas_cap_wei=cap,source=source)
            if gross<=cap: return
            try: simulate(borrower,shares,loan,deadline,swap_out,cap+1,max_fee)
            except Exception as err:
                log('guard_revert',borrower=borrower,error=str(err)[:180])
                return
            if MODE=='paper':
                log('paper_sim',result='success',borrower=borrower,gross_wei=gross,cap_wei=cap)
            else:
                send_live(borrower,shares,loan,deadline,swap_out,gross,cap,max_fee,int(e['blockNumber'],16))
            return
    log('opportunity_skip',reason='no_profitable_sim',borrower=borrower,source=source)

def process(e, source):
    if e.get('removed'):
        log('reorg',tx=e.get('transactionHash'))
        scan_recent()
        return
    borrower,shares,repay=event_details(e)
    log('detected',borrower=borrower,shares=shares,repay_wei=repay,
        tx=e['transactionHash'],block=int(e['blockNumber'],16),source=source)
    state['seen'][borrower.lower()]=e
    save_state()
    check(e,source)

def scan_recent():
    head=int(rpc('eth_blockNumber',[]),16)
    logs=rpc('eth_getLogs',[{'address':PAIR,'fromBlock':hex(max(0,head-10_000)),
        'toBlock':hex(head),'topics':[TOPIC_LIQ]}])
    for e in logs[-20:]:
        borrower,_,_=event_details(e)
        old=state['seen'].get(borrower.lower())
        if not old or old['transactionHash']!=e['transactionHash']:
            process(e,'rescan')
    for e in list(state['seen'].values())[-20:]:
        if int(e['blockNumber'],16)>=head-10_000:
            check(e,'safety')

def poll_feed():
    q={'address':PAIR,'topic0':TOPIC_LIQ,'timeout':'55'}
    if state.get('cursor'): q['after']=state['cursor']
    url=FEED+'?'+urllib.parse.urlencode(q)
    with urllib.request.urlopen(url,timeout=65) as resp: ans=json.load(resp)
    if ans.get('cursor'): state['cursor']=ans['cursor']; save_state()
    if ans.get('gap'):
        log('feed_gap',cursor=state.get('cursor'))
        scan_recent()
    for e in ans.get('logs',[]): process(e,'feed')

def main():
    log('start',mode=MODE,executor=EXEC if MODE=='live' else PAPER_EXEC,
        pair=PAIR,topic0=TOPIC_LIQ,gas_limit=GAS_LIMIT)
    last_safety=0
    while True:
        try:
            if time.monotonic()-last_safety>=600:
                scan_recent();last_safety=time.monotonic()
            poll_feed()
        except urllib.error.HTTPError as exc:
            log('feed_http_error',status=exc.code)
            if exc.code in (429,503):
                try: scan_recent()
                except Exception as x: log('rescan_error',error=str(x)[:250])
            time.sleep(20)
        except Exception as exc:
            log('loop_error',error=str(exc)[:250])
            try: scan_recent()
            except Exception as x: log('rescan_error',error=str(x)[:250])
            time.sleep(20)

if __name__=='__main__': main()
