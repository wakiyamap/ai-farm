#!/usr/bin/env python3
"""Analyze bvb_quotes.jsonl: per-source per-leg worst-case net, and
cross-source round trips (A->B on bridge X + B->A on bridge Y).
Rule from decision: at 200 USD, a round trip net >= +0.30% of principal
(i.e. >= 0.60 USD on 200) is a keeper; below = dead_end."""
import json, collections, itertools

rows = [json.loads(l) for l in open('/srv/farm/ws/scratch/bvb_quotes.jsonl')]
# latest OK row per (src, from, to, amt); src relay-retry counts as relay
best = {}
for r in rows:
    if 'err' in r: continue
    src = 'relay' if r['src'] == 'relay-retry' else r['src']
    best[(src, r['from'], r['to'], r['amt'])] = r
errs = {}
for r in rows:
    if 'err' not in r: continue
    src = 'relay' if r['src'] == 'relay-retry' else r['src']
    k = (src, r['from'], r['to'], r['amt'])
    if k not in best: errs[k] = r['err'][:70]

CH = ['ethereum','base','arbitrum','optimism','polygon','avalanche','bsc','hyperevm']
SRCS = ['relay','across','stargateV2','cctp','mayan']

print("=== per-leg table (worst-case recv_min - amount, USD; gas_usd listed) ===")
for src in SRCS:
    have = [k for k in best if k[0] == src]
    print(f"\n-- {src}: {len(have)}/112 legs quoted")
    for k in sorted(have, key=lambda k: (k[1], k[2], k[3])):
        r = best[k]
        net = r['recv_min'] - r['amt']
        print(f"  {k[1]:>9}->{k[2]:<9} {k[3]:>4} recv_min={r['recv_min']:>9.2f} d={net:+.3f} gas={r['gas_usd']:.3f}")

print("\n=== round trips at 200 USD (worst-case recv, both legs' origin gas deducted) ===")
results = []
for (a, b) in itertools.combinations(CH, 2):
    for s1 in SRCS:
        k1 = (s1, a, b, 200); k2x = (s1, b, a, 200)
        if k1 in best and k2x in best:
            r1, r2 = best[k1], best[k2x]
            net = (r1['recv_min'] + r2['recv_min'] - 400) - r1['gas_usd'] - r2['gas_usd']
            results.append((net, f"{a}->{b} & back on {s1} (same bridge)", f"{net/200*100:+.3f}%"))
    for s1 in SRCS:
        for s2 in SRCS:
            if s1 == s2: continue
            k1 = (s1, a, b, 200); k2 = (s2, b, a, 200)
            if k1 in best and k2 in best:
                r1, r2 = best[k1], best[k2]
                net = (r1['recv_min'] + r2['recv_min'] - 400) - r1['gas_usd'] - r2['gas_usd']
                results.append((net, f"{a}->{b} on {s1} + {b}->{a} on {s2}", f"{net/200*100:+.3f}%"))
results.sort(reverse=True)
for net, desc, pct in results[:25]:
    print(f"  {pct:>8} {net:+7.2f} USD  {desc}")
keepers = [x for x in results if x[0] >= 0.60]
print(f"\nkeepers (>= +0.30% = >= 0.60 USD on 200): {len(keepers)} / {len(results)} round trips")
for net, desc, pct in keepers: print("  KEEP", pct, desc)
