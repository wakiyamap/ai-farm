"""Timing of single-earmark pools: block -> UTC via ref block/time (12 s), caller recipient.
usage: rc-earmark-times.py logs.json bps ref_block ref_unix"""
import json, sys, collections, datetime
logs = json.load(open(sys.argv[1])); bps = int(sys.argv[2]); rb = int(sys.argv[3]); rt = int(sys.argv[4])
stakers = {'0x3fe65692bfcd0e6cf84cb1e7d24108e434a7587e', '0xcf50b810e57ac33b91dcf525c6ddd9881b139332',
           '0x1389388d01708118b497f59521f6943be2541bb7'}
bytx = collections.defaultdict(list)
for l in logs:
    bytx[l['transactionHash']].append(('0x' + l['topics'][2][-40:], int(l['data'], 16) / 1e18, int(l['blockNumber'], 16)))
out = []
for tx, rows in bytx.items():
    tot = sum(a for _, a, _ in rows)
    exp = tot * bps / 10000
    agg = collections.defaultdict(float)
    for r, a, _ in rows: agg[r] += a
    caller = min(agg.items(), key=lambda kv: abs(kv[1] - exp))
    if caller[1] < 20: continue
    b = rows[0][2]
    ts = datetime.datetime.utcfromtimestamp(rt - (rb - b) * 12)
    out.append((b, ts.strftime('%a %m-%d %H:%M'), caller[0], round(caller[1], 1), len([1 for r, a in agg.items() if r not in stakers and a > tot * 0.05])))
out.sort()
for o in out: print(*o)
print('n', len(out), 'sum', round(sum(o[3] for o in out), 1))
