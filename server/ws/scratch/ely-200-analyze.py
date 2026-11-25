"""Lead 200 analyzer: pairwise mid spreads and counted gaps (edge>0 for >=3 consecutive ~2s samples)."""
import json, math
from itertools import combinations
from datetime import datetime

S = "/srv/farm/ws/scratch/ely-200-samples.jsonl"
rows = []
with open(S) as f:
    for line in f:
        try: r = json.loads(line)
        except Exception: continue
        if r.get("p") and len(r["p"]) >= 6: rows.append(r)
print(f"rounds kept: {len(rows)}")
if len(rows) < 10:
    raise SystemExit("too few samples")

T0 = rows[0]["t"]; TN = rows[-1]["t"]
print(f"window: {(TN-T0)/60:.1f} min, blocks {rows[0]['blk']}..{rows[-1]['blk']}")

CL = ["aero100", "ramses"]
ORACLE = ["metric15", "metric19", "avrA", "avrB"]
ALL = CL + ORACLE
FEE_STATIC = {"metric15": 0, "metric19": 0, "avrA": 500, "avrB": 500}  # ppm; AVR best-tier, metric 0 (bid/ask embeds fee)
HYPE_USD = 66.4
GAS_GAS = 350_000

def fees(rec, a, b):
    fa = rec["f"].get(a, FEE_STATIC.get(a)) if a in rec.get("f", {}) else FEE_STATIC.get(a)
    fb = rec["f"].get(b, FEE_STATIC.get(b)) if b in rec.get("f", {}) else FEE_STATIC.get(b)
    return (fa or 0) / 1e6, (fb or 0) / 1e6

def gwei(rec):
    return rec.get("gwei", 0.5)

pairs = list(combinations(ALL, 2))
# gap tracking: per pair, consecutive-sample runs with edge>0
gaps = {p: [] for p in pairs}  # list of (start_idx, run_len, max_edge, best_size_edge)
runs = {p: None for p in pairs}
feemax = {a: 0 for a in CL}
spread_hist = {p: [] for p in pairs}
for i, rec in enumerate(rows):
    for a in CL:
        f = rec["f"].get(a)
        if f: feemax[a] = max(feemax[a], f)
    for (a, b) in pairs:
        pa, pb = rec["p"].get(a), rec["p"].get(b)
        if not pa or not pb: continue
        fa, fb = fees(rec, a, b)
        for size in (100.0, 300.0):
            gasfrac = GAS_GAS * gwei(rec) * 1e-9 * HYPE_USD / size
            spread = abs(pa / pb - 1.0)
            edge = spread - fa - fb - gasfrac
            key = (a, b, size)
            if edge > 0:
                r = runs.get(key)
                if r is None: runs[key] = {"s": i, "n": 1, "mx": edge, "sum": spread, "nsp": 1}
                else:
                    r["n"] += 1; r["mx"] = max(r["mx"], edge); r["sum"] += spread; r["nsp"] += 1
            else:
                r = runs.pop(key, None)
                if r and r["n"] >= 3: gaps[(a, b)].append({"s": r["s"], "n": r["n"], "mx": r["mx"], "sp": r["sum"] / r["nsp"], "size": size})
            if spread > 0: spread_hist.setdefault(key, []).append(spread)
for key, r in runs.items():
    if r and r["n"] >= 3:
        a, b, size = key
        gaps[(a, b)].append({"s": r["s"], "n": r["n"], "mx": r["mx"], "sp": r["sum"] / r["nsp"], "size": size})

print("\nfees seen: max ppm", {k: v for k, v in feemax.items() if v})
tot_counted = 0
for (a, b), gl in sorted(gaps.items(), key=lambda kv: -len(kv[1])):
    if not gl: continue
    tot_counted += len([g for g in gl if g["size"] == 100.0])
    meds = sorted(g["mx"] for g in gl)
    print(f"{a} x {b}: {len(gl)} counted gap-sizes (>=3 samples ~6s), median max-edge {meds[len(meds)//2]*1e4:.1f}bp, "
          f"max {meds[-1]*1e4:.1f}bp, samples {(TN-T0)/3600:.2f}h")
for p in spread_hist:
    pass
# summary stats per pair: median spread
print("\nmedian pairwise |mid spread| (bp):")
for key, hs in sorted(spread_hist.items()):
    if len(hs) > 50:
        hs.sort()
        a, b, size = key
        if size == 100.0:
            print(f"  {a:9s} x {b:9s} p50 {hs[len(hs)//2]*1e4:7.2f} p90 {hs[int(len(hs)*0.9)]*1e4:7.2f} p99 {hs[int(len(hs)*0.99)]*1e4:7.2f}")
print(f"\nTOTAL counted gaps in window: {tot_counted} -> {tot_counted/((TN-T0)/3600):.1f}/hour = {tot_counted*24/((TN-T0)/3600):.1f}/day (before fee realism)")
