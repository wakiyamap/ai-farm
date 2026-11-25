import sys, json; sys.path.insert(0,'/srv/farm/ws/scratch')
from mc import rpc
F='0x0c3c1c532F1e39EdF36BE9Fe0bE1410313E074Bf'
T0='0x0d3648bd0f6ba80134a33ba9275ac585d9d315f0ad8355cddefde31afa28d0e9'
START=112197970; HEAD=159734889
pairs=[]; reqs=0
def scan(a,b):
    global reqs
    reqs+=1
    r=rpc('eth_getLogs',[{'fromBlock':hex(a),'toBlock':hex(b),'address':F,'topics':[T0]}])
    if isinstance(r,dict):
        if b-a>50000:
            m=(a+b)//2; return scan(a,m)+scan(m+1,b)
        print('ERR',a,b,r); return []
    if len(r)>=10000 and b-a>20000:
        m=(a+b)//2; return scan(a,m)+scan(m+1,b)
    return r
CH=8_000_000
a=START
logs=[]
while a<=HEAD:
    b=min(a+CH-1,HEAD)
    logs+=scan(a,b); a=b+1
for L in logs:
    # pair address is 3rd indexed topic
    pairs.append('0x'+L['topics'][2][-40:])
print('logs',len(logs),'pairs',len(pairs),'requests',reqs)
json.dump(pairs, open('/srv/farm/ws/scratch/uv2opt_allpairs.json','w'))
print('first',pairs[:2]); print('last',pairs[-2:])
