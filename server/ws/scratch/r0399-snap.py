"""Snapshot of claimable CRV per Convex pool (caller incentive = 0.5%). Research lane, Multicall3 batches."""
import json, subprocess, sys
BOOSTER = "f403c135812408bfbe8713b5a23a04b3d48aae31"
PROXY = "989aeb4d175e16225e39e87d0d97a3360524ad80"
MC = "0xcA11bde05977b3631167028862bE2a173976CA11"
N = int(sys.argv[1]); CRV = float(sys.argv[2])

def w(x):
    return x.to_bytes(32, "big") if isinstance(x, int) else x.rjust(32, b"\0")

def agg3(calls):
    # aggregate3((address target,bool allowFailure,bytes callData)[])
    head, tails = [], []
    off = 32 * len(calls)
    for t, d in calls:
        head.append(w(off))
        el = w(bytes.fromhex(t)) + w(1) + w(96) + w(len(d)) + d + b"\0" * ((32 - len(d) % 32) % 32)
        tails.append(el); off += len(el)
    body = w(32) + w(len(calls)) + b"".join(head) + b"".join(tails)
    return "0x82ad56cb" + body.hex()

def call(data):
    r = subprocess.run(["python3", "/srv/farm/ws/tools/rpc.py", "ethereum", "eth_call", json.dumps([{"to": MC, "data": data, "gas": "0x8000000"}, "latest"]), "--lane", "research"], capture_output=True, text=True)
    res = bytes.fromhex(json.loads(r.stdout)["result"][2:])
    n = int.from_bytes(res[32:64], "big"); out = []
    for i in range(n):
        o = 64 + int.from_bytes(res[64 + 32 * i:96 + 32 * i], "big")
        ok = int.from_bytes(res[o:o + 32], "big")
        lo = o + int.from_bytes(res[o + 32:o + 64], "big")
        ln = int.from_bytes(res[lo:lo + 32], "big")
        out.append((ok, res[lo + 32:lo + 32 + ln]))
    return out

pools = []
for s in range(0, N, 150):
    calls = [(BOOSTER, bytes.fromhex("1526fe27") + w(i)) for i in range(s, min(N, s + 150))]
    for i, (ok, r) in zip(range(s, N), call(agg3(calls))):
        if ok and len(r) >= 192:
            gauge = r[64 + 12:96].hex(); rew = r[96 + 12:128].hex(); shut = int.from_bytes(r[160:192], "big")
            if not shut:
                pools.append((i, gauge, rew))
print("active pools", len(pools), file=sys.stderr)
rows = []
for s in range(0, len(pools), 60):
    chunk = pools[s:s + 60]
    calls = [(g, bytes.fromhex("33134583") + w(bytes.fromhex(PROXY))) for _, g, _ in chunk]
    for (pid, g, rew), (ok, r) in zip(chunk, call(agg3(calls))):
        c = int.from_bytes(r[:32], "big") / 1e18 if ok and len(r) >= 32 else -1
        rows.append((pid, g, rew, c))
rows.sort(key=lambda x: -x[3])
tot = sum(r[3] for r in rows if r[3] > 0)
print("claimable CRV total %.0f -> incentive %.1f CRV = %.2f USD" % (tot, tot * 0.005, tot * 0.005 * CRV))
print("failed", sum(1 for r in rows if r[3] < 0))
for pid, g, rew, c in rows[:25]:
    print(pid, "0x" + g, "0x" + rew, "claimable %.1f" % c, "incentive_usd %.2f" % (c * 0.005 * CRV))
for th in (1, 2, 5, 10, 20):
    print("pools with incentive >= %d USD:" % th, sum(1 for r in rows if r[3] * 0.005 * CRV >= th))
json.dump(rows, open("/srv/farm/ws/scratch/r0399-snap.json", "w"))
