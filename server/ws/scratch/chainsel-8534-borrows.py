import json, collections, sys
d = json.load(open(sys.argv[1]))
b = collections.defaultdict(float)
top = collections.defaultdict(list)
for p in d:
    ct = p.get('chainTvls') or {}
    for k, v in ct.items():
        if k.endswith('-borrowed') and isinstance(v, (int, float)) and v > 0:
            ch = k[:-9]
            b[ch] += v
            top[ch].append((v, p['name'], p.get('category')))
rows = sorted(b.items(), key=lambda x: -x[1])
for ch, v in rows[:90]:
    t = sorted(top[ch], reverse=True)[:3]
    print(f'{ch:22s} {v/1e6:10.1f}M  ' + '; '.join(f'{n} {x/1e6:.1f}M' for x, n, c in t))
