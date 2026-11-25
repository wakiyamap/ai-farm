#!/usr/bin/env python3
"""Timer based Revert Lend ARB/USDC liquidation trial on Arbitrum."""
import sys as _farm_sys; _farm_sys.path.append("/opt/farm/lib")  # human 2026-11-17: signer import path
import datetime
import json
import os
from pathlib import Path
import time
import urllib.request

HERE = Path(__file__).resolve().parent
MODE = os.environ.get('BOT_MODE', 'paper')
LANE = os.environ.get('RPC_LANE', 'paper')
RELAY = os.environ['RPC_RELAY_URL'].rstrip('/')
CHAIN = 'arbitrum'
VAULT = '0x74e6afef5705beb126c6d3bf46f8fad8f3e07825'
USDC = '0xaf88d065e77c8cc2239327c5edb3a432268e5831'
ARB = '0x912ce59144191c1204e64559fe8253a0e49e6548'
WETH = '0x82af49447d8a07e3bd95bd0d56f35241523fbab1'
MULTICALL = '0xca11bde05977b3631167028862be2a173976ca11'
BORROW = '0xbf608caf5cc20aaeea74ecfce286b511362b0ecbaa0e56ded00f76f7e2e39c44'
ADD = '0xe5b6779c4a18cbf7e4bce3a6c308b215c678f316648b832318a03841664fc2e9'
LIQUIDATE = '0xed06e9846d4eeeab7ba0ef79c085287948a840eb50234fd66642450a000447ca'
PAPER_EXEC = '0xb464f7314d55ec6a9a0cf6f7f6df17af8ed5b352'
PAPER_OWNER = '0xc0ffee0000000000000000000000000000000057'
EXEC = os.environ.get('EXECUTOR_ADDR_ARBITRUM') or os.environ.get('EXECUTOR_ADDR')
if MODE == 'live' and not EXEC:
    raise SystemExit('EXECUTOR_ADDR_ARBITRUM or EXECUTOR_ADDR required in live mode')
RUNTIME = (HERE/'executor-runtime.hex').read_text().strip()
if not RUNTIME.startswith('0x'):
    raise SystemExit('missing paper executor runtime')
LOG = HERE/'logs'/'bot.jsonl'
STATE = HERE/'state'/'state.json'
CU = HERE/'state'/'cu.json'
LOG.parent.mkdir(exist_ok=True)
STATE.parent.mkdir(exist_ok=True)
_id = 0
CU_COST = {'eth_call':20, 'eth_estimateGas':20, 'eth_getLogs':60,
           'eth_blockNumber':10, 'eth_gasPrice':10, 'eth_getTransactionReceipt':20}

class BudgetEnd(Exception): pass

def log(ev, **kw):
    with LOG.open('a') as f:
        f.write(json.dumps({'ts':time.time(),'ev':ev,**kw},separators=(',',':'),default=str)+'\n')

def rpc(method, params):
    global _id
    day = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    try: b = json.loads(CU.read_text())
    except Exception: b = {'day':day,'cu':0}
    if b.get('day') != day: b = {'day':day,'cu':0}
    cost = CU_COST.get(method,20)
    if b['cu'] + cost > 80000: raise BudgetEnd('80,000 relay CU/day cap')
    b['cu'] += cost
    CU.write_text(json.dumps(b))
    _id += 1
    payload = json.dumps({'jsonrpc':'2.0','id':_id,'method':method,'params':params}).encode()
    req = urllib.request.Request(f'{RELAY}/{CHAIN}?lane={LANE}',payload,
                                 {'content-type':'application/json'})
    with urllib.request.urlopen(req,timeout=35) as resp: ans = json.load(resp)
    if 'error' in ans: raise RuntimeError(f'{method}: {ans["error"]}')
    return ans['result']

def w(n): return format(n,'064x')
def aw(a): return a.lower().removeprefix('0x').zfill(64)
def at(h,i): return int(h[2+64*i:2+64*(i+1)],16)
def addr(h,i): return '0x'+h[2+64*i+24:2+64*(i+1)].lower()

def call(to,data,frm=None,override=None):
    tx={'to':to,'data':data}
    if frm: tx['from']=frm
    p=[tx,'latest']
    if override: p.append(override)
    return rpc('eth_call',p)

def aggregate(ids):
    """Multicall3.tryAggregate, one batched loanInfo read per 25 loans."""
    calls=['0x8349d6be'+w(n) for n in ids]
    starts=[]; acc=32*len(calls)
    for data in calls:
        starts.append(acc)
        size=(len(data)-2)//2
        acc += 96 + ((size+31)//32)*32
    enc='0xbce38bd7'+w(0)+w(64)+w(len(calls)) + ''.join(w(x) for x in starts)
    for data in calls:
        size=(len(data)-2)//2
        enc += aw(VAULT)+w(64)+w(size)+data[2:].ljust(((size+31)//32)*64,'0')
    h=call(MULTICALL,enc)[2:]
    n=min(int(h[64:128],16),len(calls))
    out=[]
    for i in range(n):
        start=128+int(h[128+i*64:192+i*64],16)*2
        ok=int(h[start:start+64],16)!=0
        off=int(h[start+64:start+128],16)
        length=int(h[start+off*2:start+off*2+64],16)
        data='0x'+h[start+off*2+64:start+off*2+64+length*2]
        out.append((at(data,0),at(data,3),at(data,4)) if ok and len(data)>=2+5*64 else (0,0,0))
    return out+[(0,0,0)]*(len(ids)-len(out))

def load_state():
    seed=json.loads((HERE/'seed-tokenids.json').read_text())
    try: s=json.loads(STATE.read_text())
    except Exception: s={}
    s['ids']=sorted(set(seed+s.get('ids',[])))
    s.setdefault('cursor',None)
    s.setdefault('cooldown',{})
    return s

def save(s): STATE.write_text(json.dumps(s,separators=(',',':')))

def discover(s):
    head=int(rpc('eth_blockNumber',[]),16)
    lo=s['cursor']+1 if s['cursor'] is not None else head-5000
    if lo>head:return
    ids=set(s['ids'])
    total=0
    for first in range(lo,head+1,5000):
        last=min(head,first+4999)
        logs=rpc('eth_getLogs',[{'address':VAULT,'fromBlock':hex(first),'toBlock':hex(last),
                                 'topics':[[BORROW,ADD]]}])
        total+=len(logs)
        ids.update(int(x['topics'][1],16) for x in logs if len(x['topics'])>1)
    s['ids']=sorted(ids)
    s['cursor']=head
    log('discovery',new_logs=total,lo=lo,hi=head,known=len(ids))

def position_route(token_id):
    manager=addr(call(VAULT,'0xb44a2722'),0)
    p=call(manager,'0x99fbab88'+w(token_id))
    token0=addr(p,2)
    if token0 not in (ARB,WETH) or addr(p,3)!=USDC:return None
    fee=at(p,4)
    factory=addr(call(manager,'0xc45a0155'),0)
    pool=addr(call(factory,'0x1698ee82'+aw(token0)+aw(USDC)+w(fee)),0)
    if pool=='0x'+'0'*40:return None
    return token0,pool

def price_usd():
    # Aave's Arbitrum Chainlink oracle, from the deployed PoolAddressesProvider.
    aave='0x794a61358d6845594f94dc1db02a252b5b4814ad'
    provider=addr(call(aave,'0x0542975c'),0)
    oracle=addr(call(provider,'0xfca513a8'),0)
    weth='0x82af49447d8a07e3bd95bd0d56f35241523fbab1'
    return at(call(oracle,'0xb3596f07'+aw(weth)),0)/1e8

def data(token_id,cost,min_profit,max_fee,token0,pool):
    deadline=int(time.time())+120
    return ('0x8af7f1ea'+aw(VAULT)+aw(pool)+aw(USDC)+aw(token0)+w(token_id)+
            w(cost)+w(min_profit)+w(max_fee)+w(deadline))

def sim(tx,override):
    p=[tx,'latest']+([override] if override else [])
    return at(rpc('eth_call',p),0)

def winner_block(token_id,our_hash,send_block):
    head=int(rpc('eth_blockNumber',[]),16)
    xs=rpc('eth_getLogs',[{'address':VAULT,'fromBlock':hex(max(0,send_block-20)),
                            'toBlock':hex(max(head,send_block)),
                            'topics':[LIQUIDATE,'0x'+w(token_id)]}])
    ours=[int(x['blockNumber'],16) for x in xs if x['transactionHash'].lower()==our_hash.lower()]
    return min(ours) if ours else min((int(x['blockNumber'],16) for x in xs),default=None)

def send_live(s,token_id,tx,gas_limit,max_fee,priority,gross):
    import farmbot_signer
    reply=farmbot_signer.send(CHAIN,EXEC,tx['data'],0,gas_limit,max_fee,
                              max_priority_fee_per_gas=priority)
    h=reply.get('txHash') if isinstance(reply,dict) else None
    if not h:
        log('signer_reject',token_id=token_id,reply=reply);return
    receipt=None
    for _ in range(90):
        time.sleep(1)
        receipt=rpc('eth_getTransactionReceipt',[h])
        if receipt:break
    if not receipt:
        log('send_result',token_id=token_id,hash=h,result='unknown',gas_used=None,winner_block=None);return
    block=int(receipt['blockNumber'],16)
    try:winner=winner_block(token_id,h,block)
    except Exception:winner=None
    used=int(receipt['gasUsed'],16)
    log('send_result',token_id=token_id,hash=h,
        result='won' if int(receipt['status'],16) else 'lost',
        gas_used=used,gas_cost_wei=used*int(receipt['effectiveGasPrice'],16),
        send_block=block,winner_block=winner,
        blocks_after_winner=(block-winner if winner is not None else None),gross_usd=gross)
    s['cooldown'][str(token_id)]=time.time()+600

def attempt(s,token_id,cost,value):
    if s['cooldown'].get(str(token_id),0)>time.time():return
    gross_proxy=(value-cost)/1e6
    log('opportunity_detected',token_id=token_id,cost_usdc=cost/1e6,
        nominal_bonus_usdc=gross_proxy)
    if cost<=0 or cost>49_000_000_000 or gross_proxy<=0:return
    route=position_route(token_id)
    if not route:
        log('opportunity_skip',token_id=token_id,reason='different_pool');return
    token0,pool=route
    owner_addr=owner() if MODE=='live' else PAPER_OWNER
    exec_addr=EXEC if MODE=='live' else PAPER_EXEC
    override=None if MODE=='live' else {PAPER_EXEC:{'code':RUNTIME}}
    flash_amount=min(50_000_000_000,cost+max(10000,cost//100))
    tx={'from':owner_addr,'to':exec_addr,'data':data(token_id,flash_amount,1,1_000_000_000,token0,pool),
        'gas':hex(3_000_000)}
    gross=sim(tx,override)/1e6
    est_params=[{'from':owner_addr,'to':exec_addr,'data':tx['data']},'latest']
    if override:est_params.append(override)
    estimate=int(rpc('eth_estimateGas',est_params),16)
    gas_limit=(estimate*5+3)//4
    eth_price=price_usd()
    gas_price=int(rpc('eth_gasPrice',[]),16)
    priority=min(10_000_000,int(gross/eth_price*1e18*0.25/gas_limit))
    max_fee=min(100_000_000,gas_price*2+priority)
    gas_cap=gas_limit*max_fee/1e18*eth_price
    if max_fee<gas_price+priority or gas_cap>=1 or gross<=gas_cap:
        log('opportunity_skip',token_id=token_id,reason='fee_bound',gross_usd=gross,
            gas_cap_usd=gas_cap,gas_limit=gas_limit,max_fee=max_fee);return
    tx['data']=data(token_id,flash_amount,int(gas_cap*1.25*1e6)+1,max_fee,token0,pool)
    tx['gas']=hex(gas_limit)
    sim(tx,override)
    log('opportunity',token_id=token_id,token0=token0,pool=pool,gross_usd=gross,gas_cap_usd=gas_cap,
        max_fee=max_fee,priority=priority,gas_limit=gas_limit,mode=MODE)
    if MODE=='live':send_live(s,token_id,tx,gas_limit,max_fee,priority,gross)
    else:log('paper_sim',token_id=token_id,result='success',gross_usd=gross)
    s['cooldown'][str(token_id)]=time.time()+600

def owner():
    import farmbot_signer
    a=farmbot_signer.my_address()
    a=a.get('address') if isinstance(a,dict) else a
    if not isinstance(a,str) or len(a)!=42:raise RuntimeError('signer address unavailable')
    return a

def main():
    s=load_state();log('start',mode=MODE,known=len(s['ids']))
    next_discovery=0
    while True:
        start=time.time()
        try:
            if start>=next_discovery:
                discover(s);next_discovery=start+900
            active_ids=[];underwater=[]
            for off in range(0,len(s['ids']),250):
                ids=s['ids'][off:off+250]
                for token_id,(debt,cost,value) in zip(ids,aggregate(ids)):
                    if debt>0:active_ids.append(token_id)
                    if cost>0 and value>cost:underwater.append((token_id,cost,value))
            log('scan',known=len(s['ids']),active=len(active_ids),underwater=len(underwater))
            # A later Borrow/Add event reintroduces a position that becomes active again.
            s['ids']=active_ids
            for token_id,cost,value in sorted(underwater,key=lambda x:x[2]-x[1],reverse=True)[:3]:
                try:attempt(s,token_id,cost,value)
                except BudgetEnd:raise
                except Exception as e:log('simulate_revert',token_id=token_id,error=str(e)[:350])
            save(s)
        except BudgetEnd as e:
            log('read_budget_end',error=str(e));time.sleep(3600)
        except Exception as e:
            log('cycle_error',error=str(e)[:350])
        time.sleep(max(1,30-(time.time()-start)))

if __name__=='__main__':main()
