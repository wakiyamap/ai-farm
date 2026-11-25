#!/usr/bin/env python3
"""Net token flows of the tx sender EOA and the called contract, per tx (ERC20 Transfer logs + native value)."""
import json, os, sys, urllib.request, collections
RELAY = os.environ["RPC_RELAY_URL"]
TR = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
WD = "0x7fcf532c15f0a6db0bd6d0e038bea71d30d808c7d98cb3bf7268a95bf5081b65"  # Withdrawal(address,uint256)
def rpc(method, params):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    req = urllib.request.Request(f"{RELAY}/hyperevm?lane=research", data=body, headers={"content-type": "application/json"})
    r = json.load(urllib.request.urlopen(req, timeout=60))
    if "error" in r: raise RuntimeError(r["error"])
    return r["result"]
rows = json.load(open("/srv/farm/ws/scratch/lq2-felix-txs.json"))
want = sys.argv[1:]  # tx hashes
AGG = []
for r in rows:
    if want and r["tx"] not in want: continue
    rc = rpc("eth_getTransactionReceipt", [r["tx"]])
    me = {r["from"].lower(), r["to"].lower()}
    net = collections.defaultdict(int)
    flows = []
    for l in rc["logs"]:
        if l["topics"][0] == TR and len(l["topics"]) == 3:
            f = "0x" + l["topics"][1][26:]; t = "0x" + l["topics"][2][26:]; v = int(l["data"], 16)
            tok = l["address"].lower()
            if f in me: net[tok] -= v
            if t in me: net[tok] += v
            flows.append((tok[:8], f[:8], t[:8], v))
    print(r["tx"][:12], r["from"][:8], r["to"][:8], "feUSD", round(r["words"][1], 1), "gasHYPE", round(r["gas"] * r["gp"] / 1e18, 6),
          {k: v for k, v in net.items() if v})
    if len(want) == 1:
        for f in flows: print("   ", f)
    AGG.append({"tx": r["tx"], "block": r["block"], "from": r["from"], "to": r["to"], "feusd": r["words"][1], "price": r["words"][4],
                "gas_hype": r["gas"] * r["gp"] / 1e18, "net": {k: v for k, v in net.items() if v}})
json.dump(AGG, open("/srv/farm/ws/scratch/lq2-felix-pnl.json", "w"))
dec = {}
for a in AGG:
    for k in a["net"]:
        if k not in dec:
            try: dec[k] = int(rpc("eth_call", [{"to": k, "data": "0x313ce567"}, "latest"]), 16)
            except Exception: dec[k] = 18
print("decimals", dec)
per = collections.defaultdict(lambda: collections.defaultdict(float))
for a in AGG:
    p = per[a["from"]]; p["n"] += 1; p["feusd"] += a["feusd"]; p["gas_usd"] += a["gas_hype"] * a["price"]
    for k, v in a["net"].items():
        usd = v / 10 ** dec[k] * (a["price"] if k == "0x5555555555555555555555555555555555555555" else 1)
        p["net_" + k[:8]] += usd
for k, v in per.items(): print(k, {x: round(y, 3) for x, y in v.items()})
