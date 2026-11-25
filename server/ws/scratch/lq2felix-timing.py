#!/usr/bin/env python3
import json, os, urllib.request, collections, statistics
RELAY = os.environ["RPC_RELAY_URL"]
A = json.load(open("/srv/farm/ws/scratch/lq2-felix-pnl.json"))
def rpc(method, params):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    req = urllib.request.Request(f"{RELAY}/hyperevm?lane=research", data=body, headers={"content-type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=60))["result"]
b0, b1 = A[0]["block"], A[-1]["block"]
t0 = int(rpc("eth_getBlockByNumber", [hex(b0), False])["timestamp"], 16)
t1 = int(rpc("eth_getBlockByNumber", [hex(b1), False])["timestamp"], 16)
spb = (t1 - t0) / (b1 - b0)
print("sec/block", round(spb, 3), "window days", round((t1 - t0) / 86400, 2))
byblock = collections.Counter(a["block"] for a in A)
multi = [b for b, k in byblock.items() if k > 1]
print("blocks with >1 redemption", len(multi), [(b, [x["from"][:8] for x in A if x["block"] == b]) for b in multi][:10])
gaps = [A[i]["block"] - A[i - 1]["block"] for i in range(1, len(A)) if A[i]["block"] - A[i - 1]["block"] < 2000]
print("intra-burst gaps blocks: median", statistics.median(gaps), "p10", sorted(gaps)[len(gaps) // 10], "min", min(gaps), "n", len(gaps))
# profit per tx distribution (USDT0 6dp)
U = "0xb8ce59fc3717ada4c02eadf9682a9e934f625ebb"
p = sorted(a["net"].get(U, 0) / 1e6 - a["gas_hype"] * a["price"] for a in A if U in a["net"])
print("net USD/tx after gas (n=%d): median %.3f p90 %.3f max %.3f min %.3f sum %.2f" % (len(p), statistics.median(p), p[int(len(p) * .9)], p[-1], p[0], sum(p)))
