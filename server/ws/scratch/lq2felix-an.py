#!/usr/bin/env python3
import json, os, sys, urllib.request, collections
RELAY = os.environ["RPC_RELAY_URL"]
logs = json.load(open("/srv/farm/ws/scratch/lq2-felix.json"))
red = [l for l in logs if l["topics"][0].startswith("0xc8f82a38")]
print("redemption logs", len(red), "topics", len(red[0]["topics"]), "data words", (len(red[0]["data"]) - 2) // 64)
txs = collections.OrderedDict()
for l in red:
    txs.setdefault(l["transactionHash"], []).append(l)
print("txs", len(txs))
def rpc(method, params):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    req = urllib.request.Request(f"{RELAY}/hyperevm?lane=research", data=body, headers={"content-type": "application/json"})
    r = json.load(urllib.request.urlopen(req, timeout=60))
    if "error" in r: raise RuntimeError(r["error"])
    return r["result"]
lim = int(sys.argv[1]) if len(sys.argv) > 1 else 40
rows = []
for i, (h, ls) in enumerate(txs.items()):
    w = [int(ls[0]["data"][2 + 64 * k: 2 + 64 * (k + 1)], 16) for k in range((len(ls[0]["data"]) - 2) // 64)]
    row = {"tx": h, "block": int(ls[0]["blockNumber"], 16), "words": [x / 1e18 for x in w]}
    if i < lim:
        t = rpc("eth_getTransactionByHash", [h])
        rc = rpc("eth_getTransactionReceipt", [h])
        row.update({"from": t["from"], "to": t["to"], "sel": t["input"][:10], "gas": int(rc["gasUsed"], 16),
                    "gp": int(rc.get("effectiveGasPrice", "0x0"), 16), "nlogs": len(rc["logs"]), "idx": int(rc["transactionIndex"], 16)})
    rows.append(row)
json.dump(rows, open("/srv/farm/ws/scratch/lq2-felix-txs.json", "w"))
for r in rows: print(json.dumps(r))
