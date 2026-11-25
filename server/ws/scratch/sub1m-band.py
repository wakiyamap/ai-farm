#!/usr/bin/env python3
import json, re, sqlite3, sys

FARM_CHAINS = {"Ethereum","Base","Arbitrum","BSC","Polygon","Avalanche","OP Mainnet","Hyperliquid L1","Elysium"}
LOW, HIGH = 100_000, 1_000_000

def norm(s):
    s = re.sub(r'[^a-z0-9]', '', s.lower())
    for suf in ['finance','protocols','protocol','exchange','capital','global','markets','money','labs','dao','dex','defi','fi']:
        if s.endswith(suf) and len(s) > len(suf) + 2:
            s = s[:-len(suf)]
    return s

kb_names = set()
for line in open('/tmp/kb-protocols.txt'):
    n = line.strip()
    if n:
        kb_names.add(norm(n))

data = json.load(open('/tmp/llama-proto.json'))
rows = []
for p in data:
    ct = p.get('chainTvls') or {}
    farm_tvl = 0.0
    hit_chains = []
    for c in FARM_CHAINS:
        v = ct.get(c)
        if isinstance(v, (int, float)) and v > 0:
            farm_tvl += v
            hit_chains.append(c)
    if LOW <= farm_tvl < HIGH:
        rows.append((farm_tvl, p.get('name',''), p.get('category',''), p.get('module',''), ','.join(hit_chains)))

rows.sort(reverse=True)
unmatched = [r for r in rows if norm(r[1]) not in kb_names]
print(f"band 100k-1M on farm chains: {len(rows)} protocols, {len(unmatched)} with no KB name match")
for r in unmatched[:40]:
    print(f"{r[0]:>10.0f}  {r[1][:34]:34s}  {r[2][:18]:18s}  {r[4]}")
