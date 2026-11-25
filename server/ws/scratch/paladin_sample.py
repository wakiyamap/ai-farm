import json,subprocess
exec(open('/srv/farm/ws/scratch/paladin_state.py').read().split('for pool in POOLS:')[0])
seen=0
for pool in POOLS:
    raw=call(pool,'0x2d66da9f')
    n=int(raw[2+64:2+128],16)
    ls=['0x'+raw[2+128+64*i+24:2+128+64*(i+1)] for i in range(n)]
    if not ls: continue
    indices=sorted(set([0,n//2,n-1]+list(range(min(n,4)))))
    for i in indices:
        if seen>=20:break
        loan=ls[i]
        data='0xc1c55d0c'+loan[2:].rjust(64,'0')
        out=call(pool,data)
        print(json.dumps({'pool':pool,'index':i,'loan':loan,'killable':out}),flush=True)
        seen+=1
    if seen>=20:break
