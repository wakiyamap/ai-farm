import json, collections
d = json.load(open('chainsel-2685-rh-windows.json'))
rows = d['rows']
def cls(r):
    if r['win_s'] is None: return 'none'
    if r['win_blocks'] == 0: return '0'
    return '<3s' if r['win_s'] < 3 else '>=3s'
agg = collections.defaultdict(lambda: [0, 0.0])
for r in rows:
    k = (cls(r), r['feeds'][:40]); agg[k][0] += 1; agg[k][1] += r['gross_usd'] or 0
for k, v in sorted(agg.items(), key=lambda kv: -kv[1][1]): print(k, v[0], round(v[1], 1))
print('--- >=3s')
for r in rows:
    if cls(r) == '>=3s': print(r['block'], r['market'], r['repaid'], r['gross_usd'], r['win_blocks'], r['win_s'], r['how'])
print('--- <3s top gross')
for r in sorted([r for r in rows if cls(r) in ('<3s', '0')], key=lambda r: -(r['gross_usd'] or 0))[:8]:
    print(r['block'], r['market'], r['repaid'], r['gross_usd'], r['win_blocks'], r['win_s'], r['how'])
