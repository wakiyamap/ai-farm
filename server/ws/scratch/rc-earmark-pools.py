"""Per reward pool (largest recipient per tx = crvRewards): earmark count, total, gaps, caller-share.
usage: rc-earmark-pools.py logs.json bps"""
import json, sys, collections
logs = json.load(open(sys.argv[1])); bps = int(sys.argv[2])
stakers = {'0x3fe65692bfcd0e6cf84cb1e7d24108e434a7587e', '0xcf50b810e57ac33b91dcf525c6ddd9881b139332',
           '0x1389388d01708118b497f59521f6943be2541bb7'}
bytx = collections.defaultdict(list)
for l in logs:
    bytx[l['transactionHash']].append(('0x' + l['topics'][2][-40:], int(l['data'], 16) / 1e18, int(l['blockNumber'], 16)))
pools = collections.defaultdict(list)
multi = 0
for tx, rows in bytx.items():
    tot = sum(a for _, a, _ in rows)
    # pool recipients: not stakers, amount >= 50% of what each pid's earmark would be
    big = [(r, a) for r, a, _ in rows if r not in stakers and a > tot * 0.05]
    if len(big) > 1: multi += 1
    for r, a in big:
        pools[r].append((rows[0][2], a / 0.825 * bps / 10000))  # approx caller share for this pid (82.5% to pool)
print('txs', len(bytx), 'multi-pid txs', multi, 'pools', len(pools))
rows = []
for p, ev in pools.items():
    ev.sort()
    gaps = [b - a for (a, _), (b, _) in zip(ev, ev[1:])]
    rows.append((sum(c for _, c in ev), p, len(ev), max(c for _, c in ev), (sorted(gaps)[len(gaps)//2] if gaps else None)))
rows.sort(reverse=True)
print('caller_crv_7d pool n max_caller median_gap_blocks')
for r in rows[:25]:
    print(f"{r[0]:9.1f} {r[1]} {r[2]:4d} {r[3]:8.2f} {r[4]}")
