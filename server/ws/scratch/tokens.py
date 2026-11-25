import sys, json; sys.path.insert(0,'/srv/farm/ws/scratch')
from mc import aggregate, sel
pairs=json.load(open('/srv/farm/ws/scratch/uv2opt_reserves.json'))
toks=sorted({p['token0'] for p in pairs} | {p['token1'] for p in pairs})
print('distinct tokens', len(toks))
D=sel('decimals()')
dec={}
B=400
for i in range(0,len(toks),B):
    ch=toks[i:i+B]
    res,e=aggregate([(t,D) for t in ch])
    if e: print('err',i,e); continue
    for t,(ok,v) in zip(ch,res):
        dec[t]=int(v,16) if ok and len(v)>=64 else None
print('decimals fetched', sum(1 for v in dec.values() if v is not None))
json.dump(dec, open('/srv/farm/ws/scratch/uv2opt_decimals.json','w'))
