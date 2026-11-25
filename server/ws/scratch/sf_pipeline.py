"""Upcoming critical accounts for a super token: biggest deposits (= max patrician reward) and their critical time.
usage: sf_pipeline.py <network> <token>"""
import json, sys, time, urllib.request
net, tok = sys.argv[1], sys.argv[2].lower()
URL = f"https://subgraph-endpoints.superfluid.dev/{net}/protocol-v1"
def q(query):
    req = urllib.request.Request(URL, data=json.dumps({"query": query}).encode(), headers={"content-type": "application/json", "user-agent": "curl/8"})
    return json.load(urllib.request.urlopen(req, timeout=40))
now = int(time.time())
r = q('{ accountTokenSnapshots(first: 40, orderBy: maybeCriticalAtTimestamp, orderDirection: asc, where: {token: "%s", totalNetFlowRate_lt: "0", maybeCriticalAtTimestamp_gt: "%d"}) '
      '{ account { id isSuperApp } balanceUntilUpdatedAt updatedAtTimestamp totalNetFlowRate totalOutflowRate totalDeposit maybeCriticalAtTimestamp activeOutgoingStreamCount } }' % (tok, now - 4 * 3600))
if "data" not in r:
    print(json.dumps(r)[:500]); sys.exit(1)
rows = r["data"]["accountTokenSnapshots"]
print("next accounts to go critical (soonest first); deposit = max PIC reward if liquidated at the critical second")
tot7 = 0
for s in rows:
    crit = int(s["maybeCriticalAtTimestamp"])
    dep = int(s["totalDeposit"]) / 1e18
    out = int(s["totalOutflowRate"]) / 1e18 * 86400
    h = (crit - now) / 3600
    if h <= 168: tot7 += dep
    print(" %s crit_in %.1f h deposit %.4f outflow/day %.3f streams %s superapp %s" % (s["account"]["id"], h, dep, out, s["activeOutgoingStreamCount"], s["account"]["isSuperApp"]))
print("sum of deposits going critical within 7 d (first 40 rows only): %.2f" % tot7)
r = q('{ accountTokenSnapshots(first: 15, orderBy: totalDeposit, orderDirection: desc, where: {token: "%s", totalNetFlowRate_lt: "0"}) '
      '{ account { id } totalDeposit totalOutflowRate maybeCriticalAtTimestamp } }' % tok)
print("largest deposits with negative net flow:")
for s in r["data"]["accountTokenSnapshots"]:
    c = s["maybeCriticalAtTimestamp"]
    print(" %s deposit %.3f outflow/day %.2f crit_in_days %s" % (s["account"]["id"], int(s["totalDeposit"]) / 1e18, int(s["totalOutflowRate"]) / 1e18 * 86400, ("%.1f" % ((int(c) - now) / 86400)) if c else None))
