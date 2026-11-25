import json, subprocess
def getlogs(addrs,fromB,toB):
    p=subprocess.run(["python3","/srv/farm/ws/tools/rpc.py","ethereum","eth_getLogs",json.dumps([{"fromBlock":hex(fromB),"toBlock":hex(toB),"address":addrs,"topics":[]}])],capture_output=True,text=True)
    try: return json.loads(p.stdout)["result"]
    except Exception as e: print("ERR",p.stdout[:200],p.stderr[:200]); return None
addrs=[]
rows=json.load(open("scratch/imx-map.json"))
for r in rows: addrs += [r["b0"],r["b1"]]
addrs=list(dict.fromkeys(addrs))
FROM,TO=26411601,26467600
all_logs=[]
for i in range(0,len(addrs),32):
    chunk=addrs[i:i+32]
    res=getlogs(chunk,FROM,TO)
    if res is None: raise SystemExit("scan failed")
    all_logs+=res
    print(f"chunk {i//32}: {len(chunk)} addrs -> {len(res)} logs")
json.dump(all_logs,open("scratch/imx-logs7d.json","w"))
from collections import Counter
c=Counter(l["topics"][0] for l in all_logs if l.get("topics"))
for t,n in c.most_common(20): print(t,n)
