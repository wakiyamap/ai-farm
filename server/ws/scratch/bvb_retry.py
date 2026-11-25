#!/usr/bin/env python3
"""Retry pass: LiFi-routed quotes (fixed UA) + the 13 Relay 429 legs."""
import time, sys, json
sys.path.insert(0, "/srv/farm/ws/scratch")
from bvb_sweep import CHAINS, relay_quote, lifi_quote, row, TOOLS, AMOUNTS
import itertools

pairs = list(itertools.combinations(sorted(CHAINS), 2))
# LiFi jobs, 2 workers
from concurrent.futures import ThreadPoolExecutor
jobs = []
for a, b in pairs:
    for (x, y) in ((a, b), (b, a)):
        for amt in AMOUNTS:
            for t in TOOLS:
                jobs.append((x, y, amt, t))
n = [0]
def run(x, y, amt, t):
    r = lifi_quote(x, y, amt, t)
    row(t, x, y, amt, r)
    n[0] += 1
    if n[0] % 50 == 0: print("lifi done", n[0], flush=True)
with ThreadPoolExecutor(max_workers=2) as ex:
    futs = []
    for (x, y, amt, t) in jobs:
        futs.append(ex.submit(run, x, y, amt, t))
        time.sleep(0.18)
    for f in futs: f.result()
print("lifi retried:", n[0], flush=True)
# Relay retries
relay_fails = [("avalanche","optimism"),("avalanche","optimism"),
               ("bsc","polygon"),("bsc","polygon"),("polygon","bsc"),("polygon","bsc"),
               ("bsc","hyperevm"),("bsc","hyperevm"),("hyperevm","bsc"),("hyperevm","bsc"),
               ("avalanche","arbitrum"),("avalanche","arbitrum")]
name2id = {v: k for k, v in CHAINS.items()}
for i, (f, t) in enumerate(relay_fails):
    amt = 200 if i % 2 == 0 else 2000
    r = relay_quote(name2id[f], name2id[t], amt)
    row("relay-retry", name2id[f], name2id[t], amt, r)
    time.sleep(1.0)
r = relay_quote(name2id["bsc"], name2id["base"], 200)
row("relay-retry", name2id["bsc"], name2id["base"], 200, r)
print("all retries done", flush=True)
