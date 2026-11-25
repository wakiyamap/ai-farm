import subprocess, json
strats=[l.strip() for l in open('scratch/strategies.txt') if l.strip()]
def rpc(method, params):
    r = subprocess.run(["python3","/srv/farm/ws/tools/rpc.py","bsc",method,json.dumps(params)],capture_output=True,text=True)
    try: return json.loads(r.stdout)
    except: return {"err":(r.stdout+r.stderr)[:150]}
selb=subprocess.run(["cast","sig","lastEarnBlock()"],capture_output=True,text=True).stdout.strip()
vals={}
for a in strats:
    d=rpc("eth_call",[{"to":a,"data":selb},"latest"])
    r=d.get("result")
    vals[a]=int(r,16) if r and len(r)>2 else d
mx=max(v for v in vals.values() if isinstance(v,int))
print("strategies:",len(vals),"max lastEarnBlock:",mx)
rev=sorted(vals.items(),key=lambda kv:-(kv[1] if isinstance(kv[1],int) else -1))[:5]
print(rev)
errs=[k for k,v in vals.items() if not isinstance(v,int)]
print("no-getter/errors:",len(errs))
