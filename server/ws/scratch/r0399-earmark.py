import json, sys, collections
logs = json.load(open(sys.argv[1]))
if isinstance(logs, dict):
    logs = logs.get("logs", logs.get("result", []))
bytx = collections.defaultdict(list)
for l in logs:
    to = "0x" + l["topics"][2][-40:]
    amt = int(l["data"], 16) / 1e18
    bytx[(int(l["blockNumber"], 16), l["transactionHash"])].append((to, amt))
callers = collections.Counter(); callcrv = collections.defaultdict(float)
inc = []
for (b, h), tr in sorted(bytx.items()):
    tot = sum(a for _, a in tr)
    for to, a in tr:
        if tot > 0 and abs(a / tot - 0.005) < 0.0006:
            callers[to] += 1; callcrv[to] += a; inc.append((b, h, to, a, tot))
print("txs", len(bytx), "with incentive", len(inc), "first", min(bytx)[0], "last", max(bytx)[0])
print("total call incentive CRV", round(sum(x[3] for x in inc), 1))
amts = sorted(x[3] for x in inc)
if amts:
    print("per-call CRV p10/p50/p90/max", [round(amts[int(len(amts) * q)], 2) for q in (0.1, 0.5, 0.9)], round(amts[-1], 2))
for c, n in callers.most_common(15):
    print(c, n, round(callcrv[c], 1))
json.dump(inc, open(sys.argv[2], "w"))
