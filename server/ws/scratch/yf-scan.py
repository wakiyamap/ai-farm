import json, subprocess, sys
addr = [v["address"].lower() for v in json.load(open("scratch/yf-op-vaults.json"))]
TOPIC = "0x2fb611faf48b1d1b91edbba34cee10c6357adee410540e4a8f7a82b6b38673e4"
latest = 0x9860ef3
FR = latest - 302400
def getlogs(addrs):
    p = ["python3","/srv/farm/ws/tools/rpc.py","optimism","eth_getLogs",
         json.dumps([{"address":addrs,"topics":[TOPIC],"fromBlock":hex(FR),"toBlock":hex(latest)}])]
    out = subprocess.run(p, capture_output=True, text=True)
    if out.returncode != 0:
        print("ERR", out.stderr[:300]); return None
    return json.loads(out.stdout)["result"]
alllogs = []
for i in range(0, len(addr), 32):
    chunk = addr[i:i+32]
    r = getlogs(chunk)
    if r is None: sys.exit(1)
    alllogs += r
    print(f"chunk {i//32}: {len(r)} logs", flush=True)
from collections import Counter
c = Counter(l["address"].lower() for l in alllogs)
print("total StrategyReported in 7d:", len(alllogs))
for a,n in c.most_common(10): print(a, n)
json.dump(alllogs, open("scratch/yf-reported.json","w"))
