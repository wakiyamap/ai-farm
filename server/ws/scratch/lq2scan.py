#!/usr/bin/env python3
"""Topic-only scan for Liquity-v2 Redemption events on a chain. Research lane."""
import json, os, sys, time, urllib.request, collections
RELAY = os.environ["RPC_RELAY_URL"]
TOPIC = "0x84ec8e1674d62e3a8ff294b1a7f53527d2d10291765fadf94e0ce431b2334334"
chain, span, step = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
maxreq = int(sys.argv[4]) if len(sys.argv) > 4 else 40
out = sys.argv[5] if len(sys.argv) > 5 else None

def rpc(method, params):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    req = urllib.request.Request(f"{RELAY}/{chain}?lane=research", data=body, headers={"content-type": "application/json"})
    r = json.load(urllib.request.urlopen(req, timeout=60))
    if "error" in r:
        raise RuntimeError(r["error"])
    return r["result"]

head = int(rpc("eth_blockNumber", []), 16)
lo = head - span
logs, n, b = [], 0, lo
while b <= head and n < maxreq:
    e = min(b + step - 1, head)
    try:
        res = rpc("eth_getLogs", [{"fromBlock": hex(b), "toBlock": hex(e), "topics": [TOPIC]}])
    except Exception as ex:
        print("ERR", b, e, ex, file=sys.stderr); n += 1; time.sleep(1); continue
    logs += res; n += 1; b = e + 1
print(json.dumps({"chain": chain, "head": head, "from": lo, "scanned_to": b - 1, "requests": n, "logs": len(logs)}))
c = collections.Counter(l["address"].lower() for l in logs)
for a, k in c.most_common(): print(a, k)
if out:
    json.dump(logs, open(out, "w"))
