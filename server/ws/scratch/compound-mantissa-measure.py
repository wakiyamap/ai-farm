import json, os, urllib.request
RELAY = os.environ["RPC_RELAY_URL"] + "/ethereum?lane=research"
CETH = "0x4ddc2d193948926d02f9b1fe9e1daa0718270ed5"
def rpc(method, params):
    body = json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    req = urllib.request.Request(os.environ["RPC_RELAY_URL"]+ "/ethereum?lane=research",
        data=body, headers={"content-type":"application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=60).read())
def call(to, sig4, tag):
    r = rpc("eth_call", [{"to":to,"data":"0x"+sig4}, tag])
    if "error" in r: return "ERR:"+json.dumps(r["error"])[:80]
    return r["result"]
S = { "utilization":"ea21cd92","borrowRatePerBlock":"f8f9da28","interestRateModel":"f3fdb15a",
      "supplyRatePerBlock":"ae9d70b0","getCash":"3b1d21a2","totalBorrows":"47bd3718",
      "totalReserves":"8f840ddd","accrualBlockNumber":"6c540baf","utilizationOf?":"875d"}
tags = {"latest":"latest","fresh_head":"0x%x" % 26371142, "payout_blk":"0x%x" % 26365772}
out = {}
for name,tag in tags.items():
    row = {}
    for fn,sel in S.items():
        if fn.endswith("?"): continue
        row[fn] = call(CETH, sel, tag)
    out[name] = row
    print(name, {k:(int(v,16) if v.startswith('0x') and len(v)<=66 else v) for k,v in row.items()})
json.dump(out, open("scratch/compound-mantissa-state.json","w"), indent=1)
