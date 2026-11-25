#!/usr/bin/env python3
"""Final analysis: relay50 (0.5% floor, all legs) + LiFi partial quotes."""
import json, itertools, collections

def load(path, srcmap=lambda s: s):
    best = {}
    for l in open(path):
        r = json.loads(l)
        if 'err' in r: continue
        best[(srcmap(r['src']), r['from'], r['to'], r['amt'])] = r
    return best

rel = load('/srv/farm/ws/scratch/bvb_relay50.jsonl', lambda s: 'relay')
lf  = load('/srv/farm/ws/scratch/bvb_quotes.jsonl')
data = {}
data.update(lf)
data.update(rel)   # relay50 wins over older relay rows

CH = ['ethereum','base','arbitrum','optimism','polygon','avalanche','bsc','hyperevm']
SRCS = ['relay','across','stargateV2','cctp','mayan']

print("coverage per source (legs ok):")
c = collections.Counter(k[0] for k in data)
print(dict(c))

def net(r1, r2, amt):
    return (r1['recv_min'] + r2['recv_min'] - 2*amt) - r1['gas_usd'] - r2['gas_usd']
def net_center(r1, r2, amt):
    return (r1['recv'] + r2['recv'] - 2*amt) - r1['gas_usd'] - r2['gas_usd']

for AMT in (200, 2000):
    res = []
    have = [k for k in data if k[3] == AMT]
    for (a, b) in itertools.combinations(CH, 2):
        for s1 in SRCS:
            k1 = (s1, a, b, AMT); k2 = (s1, b, a, AMT)
            if k1 in data and k2 in data:
                res.append((net(data[k1], data[k2], AMT), net_center(data[k1], data[k2], AMT),
                            f"{a}->{b}<-{''} on {s1} (same)"))
            for s2 in SRCS:
                if s1 == s2: continue
                k2 = (s2, b, a, AMT)
                if k1 in data and k2 in data:
                    res.append((net(data[k1], data[k2], AMT), net_center(data[k1], data[k2], AMT),
                                f"{a}->{b} on {s1} + {b}->{a} on {s2}"))
    res.sort(key=lambda x: -x[0])
    thr = AMT * 0.003
    print(f"\n=== round trips at {AMT} USD (worst-case floor basis; threshold +{thr:.2f} USD) ===")
    for nmin, ncen, d in res[:12]:
        print(f"  floor {nmin:+7.2f} ({nmin/AMT*100:+.3f}%) center {ncen:+7.2f}  {d}")
    print(f"  combos evaluated: {len(res)}, keepers (floor>=+{thr:.2f}): {sum(1 for x in res if x[0]>=thr)}, keepers(center>=+{thr:.2f}): {sum(1 for x in res if x[1]>=thr)}")

# relay fee structure summary
print("\nrelay fee structure (from relayer_usd + gas_usd, per 200/2000):")
for k in sorted(rel, key=lambda k: (k[1], k[2], k[3]))[:10]:
    r = rel[k]
    print(f"  {k[1]:>9}->{k[2]:<9} {k[3]:>4} relayer={r['relayer_usd']:.4f} ({r['relayer_usd']/k[3]*100:.4f}%) gas={r['gas_usd']:.4f} d_center={r['recv']-k[3]:+.4f}")
