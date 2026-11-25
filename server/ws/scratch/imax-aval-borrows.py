import subprocess, json, sys

def call(to, data, tries=3):
    for _ in range(tries):
        r = subprocess.run(['python3','/srv/farm/ws/tools/rpc.py','avalanche','eth_call',
                            json.dumps([{"to":to,"data":data},"latest"])],capture_output=True,text=True)
        try:
            d = json.loads(r.stdout)
            if 'result' in d: return d['result']
        except Exception: pass
    return None

SEL_TB = subprocess.run(['cast','sig','totalBorrows()'],capture_output=True,text=True).stdout.strip()
SEL_U  = subprocess.run(['cast','sig','underlying()'],capture_output=True,text=True).stdout.strip()
SEL_B  = subprocess.run(['cast','sig','borrowBalance(address)'],capture_output=True,text=True).stdout.strip()

pools = json.load(open('/srv/farm/ws/scratch/imax-aval-pools.json'))
borrowables = sorted(set(p[k] for p in pools for k in ('borrowable0','borrowable1') if p[k] and int(p[k],16)))
res = {}
for b in borrowables:
    tb = call(b, SEL_TB)
    res[b] = int(tb,16) if tb and tb!='0x' else None
active = {k:v for k,v in res.items() if v and v > 10**15}
print("borrowables:", len(borrowables), "with totalBorrows>1e15 raw:", len(active))
for k,v in active.items():
    u = call(k, SEL_U)
    und = '0x'+u[-40:] if u and len(u)>=64 else None
    print(k, "totalBorrows raw:", v, "underlying:", und)
json.dump(res, open('/srv/farm/ws/scratch/imax-aval-totalborrows.json','w'))
