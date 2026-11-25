import json, subprocess, datetime
from collections import Counter

def rpc(method, params):
    p=subprocess.run(['python3','tools/rpc.py','ethereum',method,json.dumps(params)],capture_output=True,text=True,check=True)
    j=json.loads(p.stdout)
    if 'error' in j: raise RuntimeError(j['error'])
    return j['result']

head=rpc('eth_getBlockByNumber',['latest',False])
hn=int(head['number'],16); ht=int(head['timestamp'],16); target=ht-604800
lo=hn-60000; hi=hn
while lo+1<hi:
    m=(lo+hi)//2
    b=rpc('eth_getBlockByNumber',[hex(m),False]); t=int(b['timestamp'],16)
    if t<target:lo=m
    else:hi=m
start=rpc('eth_getBlockByNumber',[hex(hi),False])
raw=rpc('eth_call',[{'to':'0x895879b2c1fbb6ccfcd101f2d3f3c76363664f92','data':'0xb0772d0b'},'latest'])
words=[raw[2+i:2+i+64] for i in range(0,len(raw)-2,64)]
markets=['0x'+v[-40:] for v in words[2:2+int(words[1],16)]]
print('WINDOW',hn,ht,hi,int(start['timestamp'],16),datetime.datetime.fromtimestamp(int(start['timestamp'],16),datetime.timezone.utc).isoformat(),len(markets),flush=True)
# no-topic scan can reveal unexpected payout events, while a separate known-active control checks relay behavior
counts=Counter(); examples={}; total=0
for a in range(hi,hn+1,8000):
    z=min(a+7999,hn)
    logs=rpc('eth_getLogs',[{'address':markets,'fromBlock':hex(a),'toBlock':hex(z)}])
    total+=len(logs)
    for l in logs:
        topic=l['topics'][0] if l['topics'] else 'none'
        counts[topic]+=1
        examples.setdefault(topic,l)
    print('SEGMENT',a,z,len(logs),flush=True)
print('TOTAL',total,'COUNTS',json.dumps(counts),flush=True)
print('EXAMPLES',json.dumps({k:{'address':v['address'],'tx':v['transactionHash'],'block':v['blockNumber'],'topics':v['topics'],'data':v['data']} for k,v in examples.items()}),flush=True)
