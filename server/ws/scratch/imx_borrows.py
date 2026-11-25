import json, subprocess, sys
rows=json.load(open("scratch/imx-map.json"))
sel="0x47bd3718"
out=[]
def call(to,data):
    for _ in range(3):
        p=subprocess.run(["python3","/srv/farm/ws/tools/rpc.py","ethereum","eth_call",json.dumps([{"to":to,"data":data},"latest"])],capture_output=True,text=True)
        try:
            r=json.loads(p.stdout)
            if "result" in r: return r["result"]
        except Exception: pass
    return None
for row in rows:
    for k in ("b0","b1"):
        b=row[k]
        r=call(b,sel)
        v=int(r,16) if (r and len(r)>2) else 0
        out.append((b,v))
nonzero=[(b,v) for b,v in out if v and v>0]
print("borrowables:",len(out),"nonzero:",len(nonzero))
for b,v in nonzero: print(b,v)
json.dump(out,open("scratch/imx-borrows.json","w"))
