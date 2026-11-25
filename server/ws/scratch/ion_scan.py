import json, subprocess, datetime

RPC='/srv/farm/ws/tools/rpc.py'
def call(method, params):
    p=subprocess.run(['python3',RPC,'ethereum',method,json.dumps(params)],capture_output=True,text=True)
    if p.returncode: raise RuntimeError(p.stderr+' '+p.stdout)
    o=json.loads(p.stdout)
    if 'error' in o: raise RuntimeError(str(o['error']))
    return o['result']

head=int(call('eth_blockNumber',[]),16)
hblock=call('eth_getBlockByNumber',[hex(head),False])
ts=int(hblock['timestamp'],16)
target=ts-7*86400
lo,hi=head-80000,head
while lo<hi:
    mid=(lo+hi)//2
    bt=int(call('eth_getBlockByNumber',[hex(mid),False])['timestamp'],16)
    if bt<target: lo=mid+1
    else: hi=mid
start=lo
sblock=call('eth_getBlockByNumber',[hex(start),False])
print(json.dumps({'start':start,'start_time':datetime.datetime.fromtimestamp(int(sblock['timestamp'],16),datetime.timezone.utc).isoformat(),'head':head,'head_time':datetime.datetime.fromtimestamp(ts,datetime.timezone.utc).isoformat()},indent=2),flush=True)
addresses=['0x0000000000861109794c3C214B61A2B500f49ed2','0x0000000000B6ECC19F9d3dCC78Dd486230f38af2','0x000000000023D3afBd1D8305ffaC74860b5C36e4','0x0000000000d8858E1A9B373582A691dB992C23CA']
topic='0x54f9b006b19a44694e56b0d6a57f34c420bf88da7373f9d0f3380e5f4b70951e'
logs=[]
for a in addresses:
    for first in range(start,head+1,10000):
        last=min(first+9999,head)
        chunk=call('eth_getLogs',[{'address':a,'topics':[topic],'fromBlock':hex(first),'toBlock':hex(last)}])
        logs.extend(chunk)
    print(a,len([x for x in logs if x['address'].lower()==a.lower()]),flush=True)
with open('/srv/farm/ws/scratch/ion-liquidation-logs.json','w') as f:json.dump(logs,f)
print('total',len(logs),flush=True)
for x in logs[:20]: print(x['transactionHash'],int(x['blockNumber'],16),x['address'],x['topics'][1:3],x['data'],flush=True)
