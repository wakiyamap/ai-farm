import json, subprocess, sys
def call(to,data):
    for attempt in range(3):
        p=subprocess.run(["python3","/srv/farm/ws/tools/rpc.py","ethereum","eth_call",json.dumps([{"to":to,"data":data},"latest"])],capture_output=True,text=True)
        try:
            r=json.loads(p.stdout)
            if "result" in r: return r["result"]
        except Exception: pass
        print("retry",p.stdout[:120],p.stderr[:120],file=sys.stderr)
    return None
FAC="0x8C3736e2FE63cc2cD89Ee228D9dBcAb6CE5B767B"
pools=[l.strip() for l in open("scratch/imx-pools-raw.txt") if l.strip()]
pools=list(dict.fromkeys(pools))
rows=[]
for p in pools:
    r=call(FAC,"0x0572bf5f"+"0"*24+p)
    if r is None: print(p,"FAIL"); continue
    w=[r[i:i+64] for i in range(2,len(r),64)]
    lp,b0,b1=w[2][-40:],w[3][-40:],w[4][-40:]
    rows.append({"pool":p,"lendingPool":"0x"+lp,"b0":"0x"+b0,"b1":"0x"+b1})
    print(p,lp,b0,b1)
json.dump(rows,open("scratch/imx-map.json","w"),indent=1)
