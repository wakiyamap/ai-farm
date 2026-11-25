#!/usr/bin/env python3
import sys, time, itertools
sys.path.insert(0, '/srv/farm/ws/scratch')
import bvb_sweep as b
b.OUT = '/srv/farm/ws/scratch/bvb_relay50.jsonl'
jobs = []
for a, bb in itertools.combinations(sorted(b.CHAINS), 2):
    for (x, y) in ((a, bb), (bb, a)):
        for amt in (200, 2000):
            jobs.append((x, y, amt))
from concurrent.futures import ThreadPoolExecutor
done = [0]
def run(k):
    x, y, amt = k
    b.row('relay50', x, y, amt, b.relay_quote(x, y, amt))
    done[0] += 1
    if done[0] % 40 == 0: print('done', done[0], flush=True)
with ThreadPoolExecutor(max_workers=3) as ex:
    list(ex.map(run, jobs))
print('relay50 done', len(jobs), flush=True)
