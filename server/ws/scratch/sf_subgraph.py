"""Superfluid liquidations in the last N days from the protocol subgraph (keyless https).
usage: sf_subgraph.py <network> [days]
"""
import json, sys, time, urllib.request, collections

net = sys.argv[1]
days = float(sys.argv[2]) if len(sys.argv) > 2 else 7
URL = f"https://subgraph-endpoints.superfluid.dev/{net}/protocol-v1"
since = int(time.time() - days * 86400)


def q(query):
    req = urllib.request.Request(URL, data=json.dumps({"query": query}).encode(),
                                 headers={"content-type": "application/json", "user-agent": "curl/8"})
    return json.load(urllib.request.urlopen(req, timeout=40))


rows = []
last = since
while True:
    r = q('{ agreementLiquidatedV2Events(first: 1000, orderBy: timestamp, orderDirection: asc, where: {timestamp_gt: %d}) '
          '{ timestamp blockNumber transactionHash gasPrice gasUsed token liquidatorAccount targetAccount rewardAmountReceiver '
          'rewardAmount targetAccountBalanceDelta liquidationType } }' % last)
    if "data" not in r:
        print(json.dumps(r)[:600])
        sys.exit(1)
    ev = r["data"]["agreementLiquidatedV2Events"]
    rows += ev
    if len(ev) < 1000:
        break
    last = int(ev[-1]["timestamp"])
json.dump(rows, open(f"/srv/farm/ws/scratch/sf_sub_{net}.json", "w"))
print(net, "events", len(rows), "since", since)
by_type = collections.Counter(e["liquidationType"] for e in rows)
print("types (0 patrician, 1 pleb, 2 pirate):", dict(by_type))
toks = collections.defaultdict(lambda: [0, 0])
liqs = collections.defaultdict(lambda: [0, 0])
for e in rows:
    got = e["rewardAmountReceiver"].lower() == e["liquidatorAccount"].lower()
    t = toks[e["token"]]
    t[0] += 1
    l = liqs[(e["liquidatorAccount"], got)]
    l[0] += 1
    if got:
        t[1] += int(e["rewardAmount"])
for k, v in sorted(liqs.items(), key=lambda x: -x[1][0])[:12]:
    print(" liquidator", k, v[0])
for k, v in sorted(toks.items(), key=lambda x: -x[1][1])[:25]:
    print(" token", k, "events", v[0], "reward_to_liquidator_raw", v[1], "=%.4f (18dec)" % (v[1] / 1e18))
