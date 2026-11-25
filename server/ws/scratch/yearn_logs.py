import json, subprocess
addrs = [v['address'] for v in json.load(open('scratch/yearn-polygon-vaults.json'))]
HEAD = 0x5d1e3dd
FROM = HEAD - 302400
def getlogs(chunk):
    p = json.dumps([{"fromBlock": hex(FROM), "toBlock": hex(HEAD), "address": chunk}])
    r = subprocess.run(["python3","/srv/farm/ws/tools/rpc.py","polygon","eth_getLogs",p],
                       capture_output=True, text=True)
    out = json.loads(r.stdout)
    if 'error' in out: print("ERR", out['error']); return None
    return out['result']
all_logs = []
for i in range(0, len(addrs), 32):
    res = getlogs(addrs[i:i+32])
    if res is None: continue
    print(f"chunk {i//32}: {len(res)} logs")
    all_logs += res
from collections import Counter
c = Counter((l['address'].lower(), l['topics'][0][:10]) for l in all_logs)
t0 = Counter(l['topics'][0] for l in all_logs)
print("total logs 7d:", len(all_logs))
print("by topic0:", {k[:10]: v for k,v in t0.most_common(10)})
for k,v in c.most_common(15): print(k, v)
