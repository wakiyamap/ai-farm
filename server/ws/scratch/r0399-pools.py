import json, sys, collections
logs = json.load(open(sys.argv[1]))
if isinstance(logs, dict):
    logs = logs.get("logs", logs.get("result", []))
bytx = collections.defaultdict(list)
for l in logs:
    bytx[(int(l["blockNumber"], 16), l["transactionHash"])].append(("0x" + l["topics"][2][-40:], int(l["data"], 16) / 1e18, int(l["logIndex"], 16)))
# per tx there may be several earmarks (batched). Group by 4-transfer sets in logIndex order.
events = []  # (block, tx, pool_reward_contract, call_incentive, caller)
for (b, h), tr in sorted(bytx.items()):
    tr.sort(key=lambda x: x[2])
    # order per source: call(msg.sender), crvRewards, lockRewards, stakerRewards
    i = 0
    while i + 3 < len(tr) + 0 and i + 3 <= len(tr) - 1:
        c, r, lk, st = tr[i], tr[i + 1], tr[i + 2], tr[i + 3]
        tot = c[1] + r[1] + lk[1] + st[1]
        if tot > 0 and abs(c[1] / tot - 0.005) < 0.0006:
            events.append((b, h, r[0], c[1], c[0]))
            i += 4
        else:
            i += 1
print("earmark events", len(events), "in", len(bytx), "txs")
lk = collections.Counter(e[2] for e in events)
print("distinct pools", len(lk))
last = {}
big = []
gaps = collections.defaultdict(list)
for b, h, pool, inc, caller in events:
    if pool in last:
        gaps[pool].append(b - last[pool])
    if inc >= 20:
        big.append((b, h[:12], pool[:10], round(inc, 1), caller[:10], (b - last[pool]) if pool in last else None))
    last[pool] = b
print("big (>=20 CRV) events: block, tx, pool, crv, caller, blocks since pool's previous earmark")
for x in big:
    print(x)
tot = collections.defaultdict(float)
for e in events:
    tot[e[2]] += e[3]
print("top pools by weekly call incentive CRV, n earmarks, median gap blocks")
for p, v in sorted(tot.items(), key=lambda kv: -kv[1])[:15]:
    g = sorted(gaps[p])
    print(p, round(v, 1), lk[p], g[len(g) // 2] if g else None)
