import json, sys, collections
# usage: rc-earmark-analyze.py logs.json incentive_bps blocks_per_day
logs = json.load(open(sys.argv[1]))
bps = int(sys.argv[2])
bpd = float(sys.argv[3])
bytx = collections.defaultdict(list)
for l in logs:
    to = '0x' + l['topics'][2][-40:]
    amt = int(l['data'], 16) / 1e18
    bytx[l['transactionHash']].append((to, amt, int(l['blockNumber'], 16)))
callers = collections.Counter()
callamt = collections.defaultdict(float)
calls_per_tx = []
blocks = []
total_claimed = 0.0
unmatched = 0
for tx, rows in bytx.items():
    tot = sum(a for _, a, _ in rows)
    # the earmark moves: call incentive (bps), stakers, crvRewards; a tx may batch several pids
    # identify caller transfers: amount ~= bps/10000 * (amount of a sibling group). Use recipient that
    # recurs as the smallest share.
    blocks.append(rows[0][2])
    total_claimed += tot
    # caller share per tx = bps/10000 of tot (if every pid uses the same incentive)
    exp = tot * bps / 10000
    # find recipient(s) whose summed amount matches exp within 2%
    agg = collections.defaultdict(float)
    for to, a, _ in rows:
        agg[to] += a
    best = min(agg.items(), key=lambda kv: abs(kv[1] - exp))
    if abs(best[1] - exp) <= 0.02 * exp + 1e-12:
        callers[best[0]] += 1
        callamt[best[0]] += best[1]
    else:
        unmatched += 1
span = (max(blocks) - min(blocks)) or 1
days = span / bpd
print(f"txs {len(bytx)} logs {len(logs)} span_blocks {span} days {days:.2f} unmatched {unmatched}")
print(f"total moved {total_claimed:.1f} tokens; per day {total_claimed/days:.1f}; caller share/day {sum(callamt.values())/days:.2f}")
for c, n in callers.most_common(12):
    print(c, n, f"{callamt[c]:.2f}", f"per_tx {callamt[c]/n:.3f}")
