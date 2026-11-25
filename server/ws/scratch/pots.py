import sys, json; sys.path.insert(0,'/srv/farm/ws/scratch')
from mc import aggregate, sel
pairs=json.load(open('/srv/farm/ws/scratch/uv2opt_top.json'))  # top 300 by USD
BO=sel('balanceOf(address)')
def enc(a): return a[2:].lower()
B=150
res_all=[]
for i in range(0,len(pairs),B):
    ch=pairs[i:i+B]
    calls=[]
    for p in ch:
        calls.append((p['token0'], BO+'0'*24+p['pair'][2:]))
        calls.append((p['token1'], BO+'0'*24+p['pair'][2:]))
    res,e=aggregate(calls)
    if e: print('err',i,e); continue
    for j,p in enumerate(ch):
        ok0,v0=res[2*j]; ok1,v1=res[2*j+1]
        b0=int(v0,16) if ok0 and len(v0)>=64 else None
        b1=int(v1,16) if ok1 and len(v1)>=64 else None
        p['b0']=b0; p['b1']=b1
        p['pot0']=None if b0 is None else b0-p['r0']
        p['pot1']=None if b1 is None else b1-p['r1']
        res_all.append(p)
dec=json.load(open('/srv/farm/ws/scratch/uv2opt_decimals.json'))
pr=json.load(open('/srv/farm/ws/scratch/uv2opt_prices.json'))
def val(t,r):
    d=dec.get(t); p=pr.get(t)
    return 0.0 if (d is None or p is None) else r/(10**d)*p
for p in res_all:
    p['pot_usd']=val(p['token0'], max(p['pot0'] or 0,0))+val(p['token1'], max(p['pot1'] or 0,0))
res_all.sort(key=lambda p:-p['pot_usd'])
print('measured', len(res_all))
for p in res_all[:12]:
    print('pot $%9.2f  pair %s  usd_tvl $%9.2f  pot0 %d  pot1 %d' % (p['pot_usd'], p['pair'], p['usd'], p['pot0'] or 0, p['pot1'] or 0))
neg=[p for p in res_all if (p['pot0'] or 0)<0 or (p['pot1'] or 0)<0]
print('pairs with balance<reserve (anomaly):', len(neg))
json.dump(res_all[:50], open('/srv/farm/ws/scratch/uv2opt_pots.json','w'))
