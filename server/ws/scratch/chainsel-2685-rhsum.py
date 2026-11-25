import json, collections
d = json.load(open('chainsel-2685-rh-events.json'))
ev, mk = d['events'], d['markets']
U = '0x5fc5360d0400a0fd4f2af552add042d716f1d168'
rows = []
for x in ev:
    m = mk[x['id']]
    if m['loan'] != U: continue
    rep = x['repaid'] / 1e6
    lif = min(1.15, 1 / (1 - 0.3 * (1 - m['lltv'])))
    rows.append((rep, rep * (lif - 1), m['syms'][m['coll']][0], x['block'], x['caller'], bool(m['feeds'])))
rows.sort(reverse=True)
print('USDG-loan events', len(rows), 'repaid', round(sum(r[0] for r in rows)), 'gross proxy', round(sum(r[1] for r in rows)))
for r in rows[:15]: print([round(r[0], 1), round(r[1], 1)] + list(r[2:]))
b = collections.Counter('>=10k' if r[0] >= 1e4 else '1k-10k' if r[0] >= 1e3 else '100-1k' if r[0] >= 100 else '<100' for r in rows)
print(b)
g = collections.defaultdict(float)
for r in rows: g[r[2]] += r[1]
print(sorted(((round(v), k) for k, v in g.items()), reverse=True)[:8])
