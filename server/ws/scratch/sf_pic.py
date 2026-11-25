"""PIC (patrician) reward flow per token per week from the Superfluid subgraph, plus current TOGA bond.
usage: sf_pic.py <network> <farm-chain> <toga> [days]
"""
import json, sys, time, subprocess, urllib.request, collections

net, chain, toga = sys.argv[1], sys.argv[2], sys.argv[3]
days = float(sys.argv[4]) if len(sys.argv) > 4 else 28
URL = f"https://subgraph-endpoints.superfluid.dev/{net}/protocol-v1"
now = int(time.time())
since = int(now - days * 86400)


def q(query):
    req = urllib.request.Request(URL, data=json.dumps({"query": query}).encode(), headers={"content-type": "application/json", "user-agent": "curl/8"})
    return json.load(urllib.request.urlopen(req, timeout=40))


rows, last = [], since
while True:
    r = q('{ agreementLiquidatedV2Events(first: 1000, orderBy: timestamp, orderDirection: asc, where: {timestamp_gt: %d}) '
          '{ timestamp transactionHash token liquidatorAccount rewardAmountReceiver rewardAmount liquidationType } }' % last)
    ev = r["data"]["agreementLiquidatedV2Events"]
    rows += ev
    if len(ev) < 1000:
        break
    last = int(ev[-1]["timestamp"])
toks = sorted({e["token"] for e in rows})
meta = {t["id"]: t["symbol"] for t in q('{ tokens(where: {id_in: %s}) { id symbol } }' % json.dumps(toks))["data"]["tokens"]}
print(net, "events", len(rows), "days", days, "types", dict(collections.Counter(e["liquidationType"] for e in rows)))
wk = collections.defaultdict(lambda: collections.defaultdict(float))  # token -> week_index -> amount to PIC
cnt = collections.Counter()
recv = collections.defaultdict(set)
for e in rows:
    if e["liquidationType"] != 0:
        continue
    w = int((now - int(e["timestamp"])) // (7 * 86400))
    wk[e["token"]][w] += int(e["rewardAmount"]) / 1e18
    cnt[e["token"]] += 1
    recv[e["token"]].add(e["rewardAmountReceiver"])
for t, d in sorted(wk.items(), key=lambda x: -cnt[x[0]]):
    data = "0x4f47f4d8" if False else None
    cd = subprocess.run(["/opt/foundry/bin/cast", "calldata", "getCurrentPICInfo(address)", t], capture_output=True, text=True).stdout.strip()
    r = subprocess.run(["python3", "/srv/farm/ws/tools/rpc.py", chain, "eth_call", json.dumps([{"to": toga, "data": cd}, "latest"])], capture_output=True, text=True)
    try:
        h = json.loads(r.stdout)["result"][2:]
        pic, bond, rate = "0x" + h[24:64], int(h[64:128], 16) / 1e18, int(h[128:192], 16) / 1e18 * 86400
    except Exception:
        pic, bond, rate = "?", -1, -1
    print(" %s %s n=%d PIC-reward by week (0=latest): %s | receivers %s | PIC now %s bond %.6g exit/day %.6g" % (
        meta.get(t), t, cnt[t], {k: round(v, 6) for k, v in sorted(d.items())}, sorted(recv[t]), pic, bond, rate))
