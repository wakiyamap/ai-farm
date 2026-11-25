import json, subprocess, sys
from collections import Counter
addr = [v["address"] for v in json.load(open("scratch/yf-op-vaults.json"))]
T9 = "0x67f96d2854a335a4cadb49f84fd3ca6f990744ddb3feceeb4b349d2d53d32ad3"
T8 = "0x2fb611faf48b1d1b91edbba34cee10c6357adee410540e4a8f7a82b6b38673e4"
latest = 0x9860ef3
def gl(addrs, topics, days):
    fr = latest - days*7*7200
    p = ["python3","/srv/farm/ws/tools/rpc.py","optimism","eth_getLogs",
         json.dumps([{"address":addrs,"topics":[topics] if isinstance(topics,str) else [topics],"fromBlock":hex(fr),"toBlock":hex(latest)}])]
    out = subprocess.run(p, capture_output=True, text=True)
    if out.returncode != 0: print("ERR", out.stderr[:200]); return None
    return json.loads(out.stdout)["result"]
# 7d, all 112 vaults, either topic
alllogs=[]
for i in range(0,len(addr),32):
    r = gl(addr[i:i+32], [ [T8,T9] ][0], 7)
    if r is None: sys.exit(1)
    alllogs+=r
print("7d StrategyReported (8-arg OR 9-arg) across 112 vaults:", len(alllogs))
c = Counter(l["address"].lower() for l in alllogs)
print(dict(c))
# 35d on top-2 vaults for caller history
r = gl(["0xf7D66b41Cd4241eae450fd9D2d6995754634D9f3","0xd0d2Ac44Cc842079e978bB11b094764f7D0dec6A"], [T8,T9], 35)
print("35d top-2 vaults:", None if r is None else len(r))
if r:
    for l in r[-6:]: print("  blk", int(l["blockNumber"],16), l["address"][:10], l["transactionHash"])
json.dump(r or [], open("scratch/yf-rep35.json","w"))
