import json, sys, time, urllib.request
net = sys.argv[1]
tok = sys.argv[2].lower() if len(sys.argv) > 2 else None
URL = f"https://subgraph-endpoints.superfluid.dev/{net}/protocol-v1"
def q(query):
    req = urllib.request.Request(URL, data=json.dumps({"query": query}).encode(), headers={"content-type": "application/json", "user-agent": "curl/8"})
    return json.load(urllib.request.urlopen(req, timeout=40))
w = ('where: {token: "%s"}, ' % tok) if tok else ""
for ent, fields in (("newPICEvents", "timestamp blockNumber transactionHash token pic bond exitRate"),
                    ("bondIncreasedEvents", "timestamp blockNumber transactionHash token additionalBond"),
                    ("exitRateChangedEvents", "timestamp blockNumber transactionHash token exitRate")):
    r = q('{ %s(first: 25, %sorderBy: timestamp, orderDirection: desc) { %s } }' % (ent, w, fields))
    print("==", ent)
    if "data" not in r:
        print(json.dumps(r)[:400]); continue
    for e in r["data"][ent]:
        e["t"] = time.strftime("%Y-%m-%d %H:%M", time.gmtime(int(e.pop("timestamp"))))
        for k in ("bond", "additionalBond"):
            if k in e: e[k] = round(int(e[k]) / 1e18, 6)
        if "exitRate" in e: e["exit_per_day"] = round(int(e.pop("exitRate")) / 1e18 * 86400, 6)
        print(" ", e)
