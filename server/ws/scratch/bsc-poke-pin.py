import json, urllib.request, os
RELAY = os.environ["RPC_RELAY_URL"]
def rpc(method, params, chain="bsc", lane="research"):
    body = json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    req = urllib.request.Request(f"{RELAY}/{chain}?lane={lane}", data=body,
        headers={"content-type":"application/json"})
    r = json.loads(urllib.request.urlopen(req, timeout=90).read())
    if "error" in r: print("ERR", r["error"]); return None
    return r["result"]
HEAD = int(rpc("eth_blockNumber", []), 16)
T0 = "0xf7a40077ff7a04c7e61f6f26fb13774259ddf1b6bce9ecf26a8276cdd3992683"  # Claimed
logs = []
for i in range(10, 0, -1):
    a, b = HEAD - 1000*i - 999, HEAD - 1000*i
    r = rpc("eth_getLogs", [{"fromBlock":hex(a),"toBlock":hex(b),"topics":[T0]}])
    if r: logs.extend(r)
from collections import Counter
c = Counter(l["address"].lower() for l in logs)
print("Claimed logs 10k blocks:", len(logs))
print(c.most_common())
tx = rpc("eth_getTransactionByHash", ["0x7b783e74fc64268f90003115ca863677de77eee4bcafd86eb69f6e1b9ce5d3f8"])
print("Claimed1 to:", tx["to"], "from:", tx["from"])
# full logs save
json.dump([{"h":l["transactionHash"],"blk":int(l["blockNumber"],16),"addr":l["address"],"topics":l["topics"],"data":l["data"]} for l in logs], open("scratch/bsc-claimed-logs.json","w"))
