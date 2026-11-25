"""Lead 200 analyzer v2: executable two-leg edge per round, counted gaps >=3 consecutive samples."""
import json, math
from itertools import combinations

S = "/srv/farm/ws/scratch/ely-200-samples.jsonl"
rows = []
with open(S) as f:
    for line in f:
        try: r = json.loads(line)
        except Exception: continue
        if r.get("p") and len(r["p"]) >= 8: rows.append(r)
T0 = rows[0]["t"]; TN = rows[-1]["t"]
print(f"rounds kept: {len(rows)}, window {(TN-T0)/60:.1f} min, blocks {rows[0]['blk']}..{rows[-1]['blk']}")

HYPE_USD = 66.4
AVR_FEE = 0.001  # conservative dynamic-tier fee for AVR v4 legs (500..3000 ppm tier, hook-set)
results = {}   # (v1,v2,size) -> list of gap dicts
runs = {}
best_of_round = []
for i, rec in enumerate(rows):
    p = rec["p"]; f = rec.get("f", {})
    g = rec.get("gwei", 0.5)
    quotes = {}  # name -> (buy_ask, sell_bid) in USDC/WHYPE
    for name in ("aero100", "ramses"):
        fee = (f.get(name) or 0) / 1e6
        m = p[name]
        quotes[name] = (m * (1 + fee), m * (1 - fee))
    for name in ("metric15", "metric19"):
        quotes[name] = (p[name + "_a"], p[name + "_b"])  # ask to buy, bid when selling
    for name in ("avrA", "avrB"):
        m = p[name]
        quotes[name] = (m * (1 + AVR_FEE), m * (1 - AVR_FEE))
    best_round = None
    for v1 in quotes:      # buy WHYPE at v1.ask
        for v2 in quotes:
            if v1 == v2: continue
            for size in (100.0, 300.0):
                gross = quotes[v2][1] / quotes[v1][0] - 1.0
                gas_usd = 350_000 * g * 1e-9 * HYPE_USD
                edge = gross - gas_usd / size
                key = (v1, v2, size)
                if edge > 0:
                    r = runs.get(key)
                    if r is None: runs[key] = {"s": i, "n": 1, "mx": gross, "sumg": gross}
                    else:
                        r["n"] += 1; r["mx"] = max(r["mx"], gross); r["sumg"] += gross
                else:
                    r = runs.pop(key, None)
                    if r and r["n"] >= 3:
                        results.setdefault((v1, v2), []).append({"size": size, "n": r["n"], "mx": r["mx"], "avg": r["sumg"] / r["n"]})
                if size == 300.0:
                    if best_round is None or gross > best_round[0]: best_round = (gross, v1, v2)
    if best_round: best_of_round.append(best_round)
for key, r in runs.items():
    v1, v2, size = key
    if r["n"] >= 3:
        results.setdefault((v1, v2), []).append({"size": size, "n": r["n"], "mx": r["mx"], "avg": r["sumg"] / r["n"]})

hours = (TN - T0) / 3600
print(f"\nbest executable edge per round (300 USD legs): p50 {sorted(x[0] for x in best_of_round)[len(best_of_round)//2]*1e4:.1f}bp  p90 {sorted(x[0] for x in best_of_round)[int(len(best_of_round)*0.9)]*1e4:.1f}bp  max {max(x[0] for x in best_of_round)*1e4:.1f}bp")
from collections import Counter
bc = Counter(x[1] + "->" + x[2] for x in best_of_round)
print("best-route frequency:", bc.most_common(6))
gascost = 350_000 * 0.5e-9 * HYPE_USD
print(f"gas per 2-swap attempt @0.5gwei: {gascost:.3f} USD")
tot100 = tot300 = 0; usd300 = 0.0
print("\ncounted gaps (edge>0 for >=3 consecutive samples ~6s):")
for (v1, v2), gl in sorted(results.items(), key=lambda kv: -len(kv[1])):
    c100 = len([g for g in gl if g["size"] == 100.0]); c300 = len([g for g in gl if g["size"] == 300.0])
    tot100 += c100; tot300 += c300
    for g in gl:
        if g["size"] == 300.0: usd300 += g["avg"] * 300 - gascost
    print(f"  {v1} -> {v2}: {len(gl)} gaps, max gross {max(g['mx'] for g in gl)*1e4:.1f}bp, avg gross {sum(g['avg'] for g in gl)/len(gl)*1e4:.1f}bp")
print(f"\nTOTAL: {tot100} counted @100, {tot300} @300 in {hours:.2f} h -> {tot300/hours:.1f}/h = {tot300*24/hours:.0f}/day (300 USD)")
print(f"USD at 300: sum over counted {usd300:.2f} -> {usd300/hours*24:.2f} USD/day")
