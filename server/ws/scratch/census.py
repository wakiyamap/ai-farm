import sys, json; sys.path.insert(0,'/srv/farm/ws/scratch')
from mc import aggregate, sel
pairs=json.load(open('/srv/farm/ws/scratch/uv2opt_pairs_full.json'))
G=sel('getReserves()')
out=[]; fails=0; reqs=0
B=400
for i in range(0,len(pairs),B):
    chunk=pairs[i:i+B]
    res,e=aggregate([(p['pair'],G) for p in chunk])
    reqs+=1
    if e: print('batch err',i,e); fails+=1; continue
    for p,(ok,v) in zip(chunk,res):
        if not ok or len(v)<192: fails+=1; continue
        r0=int(v[0:64],16); r1=int(v[64:128],16); ts=int(v[128:192],16)
        p['r0']=r0; p['r1']=r1; p['ts']=ts
        out.append(p)
print('reqs',reqs,'with reserves data',len(out),'fails',fails)
nz=[p for p in out if p['r0']>0 and p['r1']>0]
print('nonzero reserves',len(nz))
json.dump(out, open('/srv/farm/ws/scratch/uv2opt_reserves.json','w'))
