"""Run 8980b787: short fresh sample of the Elysium USDC/WHYPE venues (aero ts100, ramses CL, metric15/19).
One JSON-RPC batch per round through the relay (research lane). 0 fork, 0 tx.
usage: r8980-sample.py <rounds> <sleep_s>"""
import json, os, sys, time, urllib.request
RELAY = os.environ["RPC_RELAY_URL"].rstrip("/") + "/elysium?lane=research"
V3 = {"aero": "0x97796d80b6a1db78632f7451196b04f307329eb6", "ramses": "0xd329b88ba62483918c3f6c9421178345cf9eebc2"}
OMM = {"m15": "0xcd82337e7d2d1ab66699457a8e25b4d8e78ca259", "m19": "0xef3ac7034eac6bf3b37d3a78b6a510c7c8ac53c0"}
SLOT0, FEE, SBSP, LIQ = "0x3850c7bd", "0xddca3f43", "0xec069057", "0x1a686502"
Q = 1.8446744073709551616e19
n, slp = int(sys.argv[1]), float(sys.argv[2])
rows = []
for i in range(n):
    calls, idx = [], []
    def add(tag, to, data):
        calls.append({"jsonrpc": "2.0", "id": len(calls), "method": "eth_call", "params": [{"to": to, "data": data}, "latest"]})
        idx.append(tag)
    for k, a in V3.items():
        add(k + "_s0", a, SLOT0); add(k + "_fee", a, FEE); add(k + "_liq", a, LIQ)
    for k, a in OMM.items():
        add(k, a, SBSP)
    calls.append({"jsonrpc": "2.0", "id": len(calls), "method": "eth_blockNumber", "params": []}); idx.append("blk")
    req = urllib.request.Request(RELAY, json.dumps(calls).encode(), {"content-type": "application/json"})
    res = json.loads(urllib.request.urlopen(req, timeout=20).read())
    by = {idx[x["id"]]: x.get("result") for x in res}
    r = {"t": time.time(), "blk": int(by["blk"], 16)}
    for k in V3:
        s = int(by[k + "_s0"][2:66], 16)
        r[k] = 1.0 / (((s / 2**96) ** 2) * 1e-12)
        r[k + "_fee"] = int(by[k + "_fee"], 16)
        r[k + "_liq"] = int(by[k + "_liq"], 16) if by.get(k + "_liq") else None
    for k in OMM:
        v = by[k]
        if v and len(v) >= 130:
            r[k + "_b"] = int(v[2:66], 16) / Q; r[k + "_a"] = int(v[66:130], 16) / Q
    rows.append(r)
    # executable two-leg edges in bp, per 1 unit, fee-inclusive, no price impact
    e = {}
    for a in V3:
        for b in V3:
            if a != b:  # buy WHYPE on a (pay price*(1+fee)), sell on b (get price*(1-fee))
                e[f"{a}>{b}"] = (r[b] * (1 - r[b + "_fee"] / 1e6) / (r[a] * (1 + r[a + "_fee"] / 1e6)) - 1) * 1e4
        for m in OMM:
            if m + "_a" in r:
                e[f"{a}>{m}"] = (r[m + "_b"] / (r[a] * (1 + r[a + "_fee"] / 1e6)) - 1) * 1e4
                e[f"{m}>{a}"] = (r[a] * (1 - r[a + "_fee"] / 1e6) / r[m + "_a"] - 1) * 1e4
    if "m15_a" in r and "m19_a" in r:
        e["m15>m19"] = (r["m19_b"] / r["m15_a"] - 1) * 1e4
        e["m19>m15"] = (r["m15_b"] / r["m19_a"] - 1) * 1e4
    r["edge"] = e
    best = max(e.items(), key=lambda kv: kv[1])
    print(i, r["blk"], f"aero {r['aero']:.4f} fee {r['aero_fee']} ramses {r['ramses']:.4f} fee {r['ramses_fee']}",
          f"m15 {r.get('m15_b', 0):.4f}/{r.get('m15_a', 0):.4f} m19 {r.get('m19_b', 0):.4f}/{r.get('m19_a', 0):.4f}",
          f"best {best[0]} {best[1]:+.2f}bp", flush=True)
    time.sleep(slp)
json.dump(rows, open("/srv/farm/ws/scratch/r8980-sample.json", "w"))
pos = [max(r["edge"].values()) for r in rows]
print("rounds", n, "best-edge>0 rounds", sum(1 for x in pos if x > 0), "max bp", max(pos), "median bp", sorted(pos)[len(pos) // 2])
