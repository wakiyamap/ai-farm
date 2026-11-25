#!/usr/bin/env python3
"""A small Aave v3 same-asset liquidation trial on Arbitrum One."""
import sys as _farm_sys; _farm_sys.path.append("/opt/farm/lib")  # human 2026-11-17: signer import path
import json
import os
from pathlib import Path
import time
import datetime
import urllib.error
import urllib.parse
import urllib.request

HERE = Path(__file__).resolve().parent
MODE = os.environ.get('BOT_MODE', 'paper')
LANE = os.environ.get('RPC_LANE', 'paper')
RELAY = os.environ['RPC_RELAY_URL'].rstrip('/')
CHAIN = 'arbitrum'
POOL = '0x794a61358d6845594f94dc1db02a252b5b4814ad'
MULTICALL = '0xca11bde05977b3631167028862be2a173976ca11'
WETH = '0x82af49447d8a07e3bd95bd0d56f35241523fbab1'
USDC = '0xaf88d065e77c8cc2239327c5edb3a432268e5831'
LIQ_TOPIC = '0xe413a321e8681d831f4dbccbca790d2952b56f977908e45be37335533e005286'
BORROW_TOPIC = '0xb3d084820fb1a9decffb176436bd02558d15fac9b0ddfed8c465bc7359d7dce0'
WITHDRAW_TOPIC = '0x3115d1449a7b732c986cba18244e897a450f61e1bb8d589cd2e69e6c8924f9f7'
PAPER_EXEC = '0xb464f7314d55ec6a9a0cf6f7f6df17af8ed5b352'
PAPER_OWNER = '0xc0ffee0000000000000000000000000000000001'
EXEC = os.environ.get('EXECUTOR_ADDR_ARBITRUM') or os.environ.get('EXECUTOR_ADDR')
if MODE == 'live' and not EXEC:
    raise SystemExit('EXECUTOR_ADDR_ARBITRUM or EXECUTOR_ADDR is required in live mode')
RUNTIME = (HERE/'executor-runtime.hex').read_text().strip()
if not RUNTIME.startswith('0x'):
    raise SystemExit('missing paper executor runtime')
LOG = HERE/'logs'/'bot.jsonl'
STATE = HERE/'state'/'state.json'
CU_FILE = HERE/'state'/'cu.json'
LOG.parent.mkdir(exist_ok=True)
STATE.parent.mkdir(exist_ok=True)
SEED = json.loads((HERE/'seed-users.json').read_text())
MAX_FEE_WEI = 100_000_000  # 0.1 gwei, far below $1 at the measured 598304 gas
MAX_COVER = {WETH: 100_000_000_000_000_000, USDC: 300_000_000}
NEAR_COUNT = 200
SCAN_INTERVAL = 3600
POLL_INTERVAL = 50  # the 55 s feed timeout makes the actual safety cadence ~55-60 s
DISCOVER_INTERVAL = 600
_id = 0
CU_COST = {'eth_call':20,'eth_estimateGas':20,'eth_getLogs':60,
           'eth_getTransactionReceipt':20,'eth_blockNumber':10,'eth_gasPrice':10}

class ReadBudgetExceeded(Exception): pass

def log(ev, **kw):
    row = {'ts':time.time(),'ev':ev,**kw}
    with LOG.open('a') as f:
        f.write(json.dumps(row,separators=(',',':'),default=str)+'\n')

def rpc(method, params):
    global _id
    day = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    try: budget = json.loads(CU_FILE.read_text())
    except Exception: budget = {'day':day,'cu':0}
    if budget['day'] != day: budget = {'day':day,'cu':0}
    cost = CU_COST.get(method,20)
    # Leave >=25k CU for the feed's independently metered stream and read-cost variance.
    if budget['cu']+cost > 75000:
        raise ReadBudgetExceeded('75k relay CU/day bot cap reached')
    budget['cu'] += cost
    CU_FILE.write_text(json.dumps(budget))
    _id += 1
    body = json.dumps({'jsonrpc':'2.0','id':_id,'method':method,'params':params}).encode()
    req = urllib.request.Request(f'{RELAY}/{CHAIN}?lane={LANE}',body,
                                 {'content-type':'application/json'})
    with urllib.request.urlopen(req,timeout=30) as resp:
        ans = json.load(resp)
    if 'error' in ans:
        raise RuntimeError(f'{method}: {ans["error"]}')
    return ans['result']

def word(n): return format(n,'064x')
def address_word(a): return a.lower().removeprefix('0x').zfill(64)
def decode_addr(h): return '0x'+h[-40:].lower()
def at(h,i): return int(h[2+i*64:2+(i+1)*64],16)
def call(to,data,from_addr=None,override=None):
    tx = {'to':to,'data':data}
    if from_addr: tx['from'] = from_addr
    p = [tx,'latest']
    if override: p.append(override)
    return rpc('eth_call',p)

def aggregate(users):
    """One Multicall3 tryAggregate of Pool.getUserAccountData per user."""
    calls = [('0xbf92857c'+address_word(a)) for a in users]
    starts = []
    acc = 32*len(calls)
    for data in calls:
        starts.append(acc)
        size = (len(data)-2)//2
        acc += 96+((size+31)//32)*32
    enc = '0xbce38bd7'+word(0)+word(64)+word(len(calls))
    enc += ''.join(word(x) for x in starts)
    for data in calls:
        size = (len(data)-2)//2
        enc += address_word(POOL)+word(64)+word(size)+data[2:].ljust(((size+31)//32)*64,'0')
    h = call(MULTICALL,enc)[2:]
    if len(h)<128:
        raise RuntimeError('short Multicall answer')
    n = min(int(h[64:128],16),len(calls))
    out = []
    for i in range(n):
        start = 128+int(h[128+i*64:192+i*64],16)*2
        ok = int(h[start:start+64],16) != 0
        off = int(h[start+64:start+128],16)
        length = int(h[start+off*2:start+off*2+64],16)
        data = '0x'+h[start+off*2+64:start+off*2+64+length*2]
        if ok and len(data)>=2+6*64:
            out.append((at(data,1),at(data,5)))  # debt, health factor
        else:
            out.append((0,0))
    return out+[(0,0)]*(len(users)-len(out))

def load_state():
    if STATE.exists():
        try: return json.loads(STATE.read_text())
        except Exception: pass
    return {'users':SEED,'near':[],'cursor_block':None,'feed_cursor':None,
            'last_scan':0,'last_poll':0,'last_discover':0,'cooldown':{}}

def save_state(s):
    tmp = STATE.with_suffix('.tmp')
    tmp.write_text(json.dumps(s,separators=(',',':')))
    tmp.replace(STATE)

def owner():
    import farmbot_signer
    a = farmbot_signer.my_address()
    a = a.get('address') if isinstance(a,dict) else a
    if not isinstance(a,str) or len(a)!=42:
        raise RuntimeError('signer my_address returned no address')
    return a

def check_config(user,reserve_index):
    c = at(call(POOL,'0x4417a583'+address_word(user)),0)
    return bool(c & (1<<(2*reserve_index))) and bool(c & (1<<(2*reserve_index+1)))

def price_usd():
    provider = decode_addr(call(POOL,'0x0542975c'))
    oracle = decode_addr(call(provider,'0xfca513a8'))
    return at(call(oracle,'0xb3596f07'+address_word(WETH)),0)/1e8

def reserves():
    h = call(POOL,'0xd1946dbc')
    n = at(h,1)
    if not (1<=n<=100): raise RuntimeError(f'bad reserve count {n}')
    arr = [decode_addr(h[2+(2+i)*64:2+(3+i)*64]) for i in range(n)]
    return {a:i for i,a in enumerate(arr)}

def calldata(user,token,cover,min_profit):
    unwrap = token == WETH
    return '0xff53549b'+address_word(user)+address_word(token)+word(cover)+word(min_profit)+word(int(unwrap))

def sim(user,token,from_addr,exec_addr,code=None,min_profit=0):
    tx = {'from':from_addr,'to':exec_addr,
          'data':calldata(user,token,MAX_COVER[token],min_profit),'gas':hex(1_200_000)}
    ov = {exec_addr:{'code':code}} if code else None
    params = [tx,'latest']+([ov] if ov else [])
    return at(rpc('eth_call',params),0)

def estimate(user,token,from_addr,exec_addr,code=None):
    tx = {'from':from_addr,'to':exec_addr,'data':calldata(user,token,MAX_COVER[token],0)}
    params = [tx,'latest']+([{exec_addr:{'code':code}}] if code else [])
    return int(rpc('eth_estimateGas',params),16)

def winner_block(user,send_block,our_hash):
    lo = max(0,send_block-12)
    hi = max(send_block,int(rpc('eth_blockNumber',[]),16))
    topic = '0x'+address_word(user)
    logs = rpc('eth_getLogs',[{'address':POOL,'fromBlock':hex(lo),'toBlock':hex(hi),
                               'topics':[LIQ_TOPIC,None,None,topic]}])
    ours = [int(x['blockNumber'],16) for x in logs
            if x['transactionHash'].lower()==our_hash.lower()]
    if ours: return min(ours)
    return min((int(x['blockNumber'],16) for x in logs),default=None)

def send_live(s,user,token,data,gas_limit,max_fee,priority,gross_usd):
    import farmbot_signer
    reply = farmbot_signer.send(CHAIN,EXEC,data,0,gas_limit,max_fee,
                                max_priority_fee_per_gas=priority)
    h = reply.get('txHash') if isinstance(reply,dict) else None
    if not h:
        log('signer_reject',user=user,token=token,reply=reply)
        return
    receipt = None
    for _ in range(90):
        time.sleep(1)
        receipt = rpc('eth_getTransactionReceipt',[h])
        if receipt: break
    if not receipt:
        log('send_result',hash=h,user=user,token=token,result='unknown',gas_used=None,winner_block=None)
        return
    b = int(receipt['blockNumber'],16)
    status = int(receipt['status'],16)
    used = int(receipt['gasUsed'],16)
    price = int(receipt['effectiveGasPrice'],16)
    try: winner = winner_block(user,b,h)
    except Exception: winner = None
    log('send_result',hash=h,user=user,token=token,result='won' if status else 'lost',
        gas_used=used,gas_cost_wei=used*price,winner_block=winner,
        blocks_after_winner=(b-winner if winner is not None else None),
        send_block=b,gross_usd=gross_usd)
    s['cooldown'][user] = time.time()+300

def attempt(s,user,hf,reserve_index):
    if s['cooldown'].get(user,0)>time.time(): return
    s['cooldown'][user] = time.time()+1800
    from_addr = owner() if MODE=='live' else PAPER_OWNER
    exec_addr = EXEC if MODE=='live' else PAPER_EXEC
    code = None if MODE=='live' else RUNTIME
    eth_usd = price_usd()
    if eth_usd<=0: return
    for token in (WETH,USDC):
        if token not in reserve_index or not check_config(user,reserve_index[token]):
            continue
        try:
            gain = sim(user,token,from_addr,exec_addr,code)
            estimated = estimate(user,token,from_addr,exec_addr,code)
            gas_limit = (estimated*5+3)//4  # Nitro: eth_estimateGas, then headroom
            gas_price = int(rpc('eth_gasPrice',[]),16)
            gross_usd = gain/1e18*eth_usd if token==WETH else gain/1e6
            gross_eth = gross_usd/eth_usd
            priority = min(10_000_000,int(gross_eth*1e18*0.25/gas_limit))
            max_fee = min(MAX_FEE_WEI,gas_price*2+priority)
            gas_usd = gas_limit*max_fee/1e18*eth_usd
            if max_fee<gas_price+priority or gas_usd>=1 or gross_usd<=gas_usd:
                log('opportunity_skip',user=user,token=token,hf=hf,gross_usd=gross_usd,
                    gas_cap_usd=gas_usd,reason='fee_bound')
                continue
            min_profit = int(gas_limit*max_fee*1.25) if token==WETH else int(gas_usd*1e6*1.25)
            data = calldata(user,token,MAX_COVER[token],min_profit)
            # Re-simulate the exact bytes that will be sent.
            gain = sim(user,token,from_addr,exec_addr,code,min_profit)
            log('opportunity',user=user,token=token,hf=hf,gross_usd=gross_usd,
                gas_cap_usd=gas_usd,gas_limit=gas_limit,max_fee=max_fee,priority=priority,
                simulated_gain=gain,mode=MODE)
            if MODE=='live':
                send_live(s,user,token,data,gas_limit,max_fee,priority,gross_usd)
            else:
                log('paper_sim',user=user,token=token,result='success',gain=gain)
            s['cooldown'][user] = time.time()+300
            return
        except ReadBudgetExceeded:
            raise
        except Exception as e:
            log('simulate_revert',user=user,token=token,hf=hf,error=str(e)[:220])

def scan_users(s,users,reserve_index,label):
    eligible = []
    near = []
    for off in range(0,len(users),200):
        batch = users[off:off+200]
        try: data = aggregate(batch)
        except ReadBudgetExceeded:
            raise
        except Exception as e:
            log('scan_error',label=label,offset=off,error=str(e)[:220]); continue
        for a,(debt,hf) in zip(batch,data):
            if debt>0 and hf>0:
                near.append((hf,a))
                if hf<10**18: eligible.append((hf,a))
    if label=='full':
        near.sort(key=lambda z:abs(z[0]-10**18))
        s['near'] = [a for _,a in near[:NEAR_COUNT]]
    log('scan',label=label,checked=len(users),debtors=len(near),underwater=len(eligible),near=len(s['near']))
    for hf,a in eligible:
        log('underwater',label=label,user=a,hf=hf/1e18)
    eligible = [(hf,a) for hf,a in eligible if hf>98*10**16]
    eligible.sort(key=lambda z:abs(z[0]-10**18))
    for hf,a in eligible[:2]:
        attempt(s,a,hf/1e18,reserve_index)

def discover(s):
    head = int(rpc('eth_blockNumber',[]),16)
    start = s['cursor_block']+1 if s['cursor_block'] is not None else max(0,head-5000)
    if start>head: return
    # Pool Borrow and Withdraw schemas: Borrow onBehalfOf=topics[2]; Withdraw user=topics[2].
    logs = rpc('eth_getLogs',[{'address':POOL,'fromBlock':hex(start),'toBlock':hex(head),
                               'topics':[[BORROW_TOPIC,WITHDRAW_TOPIC]]}])
    users = set(s['users'])
    for lg in logs:
        if len(lg.get('topics',[]))>2:
            a = decode_addr(lg['topics'][2]); users.add(a)
    added = len(users)-len(s['users'])
    s['users'] = sorted(users)
    s['cursor_block'] = head
    log('discover',from_block=start,to_block=head,logs=len(logs),added=added,universe=len(users))

def feed_wait(cursor):
    q = {'address':POOL,'topic0':LIQ_TOPIC,'timeout':'55'}
    if cursor: q['after'] = cursor
    url = 'http://127.0.0.1:8546/logs/arbitrum?'+urllib.parse.urlencode(q)
    with urllib.request.urlopen(url,timeout=65) as r:
        return json.load(r)

def main():
    s = load_state()
    idx = reserves()
    if WETH not in idx or USDC not in idx:
        raise SystemExit('Aave reserve list lacks WETH/native USDC')
    log('start',mode=MODE,universe=len(s['users']),reserve_index={WETH:idx[WETH],USDC:idx[USDC]})
    while True:
        now = time.time()
        try:
            if now-s['last_discover']>=DISCOVER_INTERVAL:
                discover(s); s['last_discover'] = now
            if now-s['last_scan']>=SCAN_INTERVAL:
                scan_users(s,s['users'],idx,'full'); s['last_scan'] = now
            elif now-s['last_poll']>=POLL_INTERVAL:
                scan_users(s,s['near'],idx,'near'); s['last_poll'] = now
            save_state(s)
            result = feed_wait(s.get('feed_cursor'))
            s['feed_cursor'] = result.get('cursor',s.get('feed_cursor'))
            if result.get('gap') or any(x.get('removed') for x in result.get('logs',[])):
                scan_users(s,s['near'],idx,'gap')
            elif result.get('logs'):
                log('feed',events=len(result['logs']),blocks=[x.get('blockNumber') for x in result['logs']])
                scan_users(s,s['near'],idx,'liquidation_feed')
        except (urllib.error.HTTPError,urllib.error.URLError,TimeoutError) as e:
            log('feed_error',error=str(e)[:180])
            try: scan_users(s,s['near'],idx,'gap')
            except Exception as e2: log('scan_error',label='gap',error=str(e2)[:180])
            time.sleep(3)
        except ReadBudgetExceeded as e:
            log('read_budget',error=str(e))
            time.sleep(600)
        except Exception as e:
            log('loop_error',error=str(e)[:250])
            time.sleep(5)
        save_state(s)

if __name__=='__main__': main()
