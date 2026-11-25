#!/usr/bin/env python3
"""Address-filtered all-topic scan, counts topic0 per address. Research lane."""
import json, os, sys, time, urllib.request, collections
RELAY = os.environ["RPC_RELAY_URL"]
chain, span, step, maxreq = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
addrs = sys.argv[5].split(",")
out = sys.argv[6] if len(sys.argv) > 6 else None
end = int(os.environ.get("TO_BLOCK", "0"))

def rpc(method, params):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    req = urllib.request.Request(f"{RELAY}/{chain}?lane=research", data=body, headers={"content-type": "application/json"})
    r = json.load(urllib.request.urlopen(req, timeout=90))
    if "error" in r:
        raise RuntimeError(r["error"])
    return r["result"]

head = end or int(rpc("eth_blockNumber", []), 16)
lo = head - span
logs, n, b = [], 0, lo
while b <= head and n < maxreq:
    e = min(b + step - 1, head)
    try:
        res = rpc("eth_getLogs", [{"fromBlock": hex(b), "toBlock": hex(e), "address": addrs}])
    except Exception as ex:
        print("ERR", b, e, str(ex)[:200], file=sys.stderr); n += 1; time.sleep(1); continue
    logs += res; n += 1; b = e + 1
print(json.dumps({"chain": chain, "head": head, "from": lo, "scanned_to": b - 1, "requests": n, "logs": len(logs)}))
c = collections.Counter((l["address"].lower(), l["topics"][0][:10]) for l in logs)
for a, k in sorted(c.items()): print(a, k)
if out:
    json.dump(logs, open(out, "w"))
