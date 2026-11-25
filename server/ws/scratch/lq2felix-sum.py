#!/usr/bin/env python3
import json, collections, statistics
rows = json.load(open("/srv/farm/ws/scratch/lq2-felix-txs.json"))
c = collections.Counter((r.get("from"), r.get("to"), r.get("sel")) for r in rows)
for k, v in c.most_common(): print(v, k)
sz = [r["words"][1] for r in rows]
print("blocks", rows[0]["block"], rows[-1]["block"], "n", len(rows))
print("feUSD redeemed total", round(sum(sz)), "median", statistics.median(sz), "max", max(sz), "min", min(sz))
# fee pct = coll_fee/(coll_sent+fee)
fees = [r["words"][3] / (r["words"][2] + r["words"][3]) * 100 for r in rows]
print("fee pct median", round(statistics.median(fees), 3), "min", round(min(fees), 3), "max", round(max(fees), 3))
prices = [r["words"][4] for r in rows]
print("price range", min(prices), max(prices))
gasc = [r["gas"] * r["gp"] / 1e18 for r in rows if "gas" in r]
print("gas HYPE median", statistics.median(gasc), "max", max(gasc), "gas units median", statistics.median([r["gas"] for r in rows]))
print("tx idx", collections.Counter(r["idx"] for r in rows).most_common(5))
# bursts: group by gaps > 1000 blocks
bursts, cur = [], [rows[0]]
for r in rows[1:]:
    if r["block"] - cur[-1]["block"] > 2000: bursts.append(cur); cur = [r]
    else: cur.append(r)
bursts.append(cur)
for b in bursts:
    print("burst", b[0]["block"], b[-1]["block"], "n", len(b), "feUSD", round(sum(x["words"][1] for x in b)), "senders", len(set(x["from"] for x in b)))
