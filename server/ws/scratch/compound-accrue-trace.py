import json, os, urllib.request
U = os.environ["RPC_RELAY_URL"]
def rpc(method, params, lane="research"):
    body = json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    req = urllib.request.Request(U+"/ethereum?lane="+lane, data=body, headers={"content-type":"application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=120).read())
TX = "0x922d32d5b69affd635ce3a08901980abe4910d45067aa0c067c4cdea66b2fa47"
tx = rpc("eth_getTransactionByHash",[TX])["result"]
print("tx from -> to, input:", tx["from"], tx["to"], tx["input"])
r = rpc("debug_traceTransaction",[TX, {"tracer":"callTracer"}])["result"]
def walk(c, depth=0):
    sel = c.get("data","0x")[2:10]
    io = {"input":c.get("data","")[:200],"output":c.get("output","")[:200]}
    print("  "*depth, c.get("type"), c.get("from","?")[:10], "->", c.get("to","?")[:10], "sel", sel,
          "val", c.get("value","0"), "err", c.get("error","")[:40])
    if c.get("to","").lower() in ("0x637329157451291387483283502445870530314902143660007".lower(),): print("      MODEL CALL data:", c.get("data","")[:200], "-> out:", c.get("output","")[:130])
    print("      io:", io)
    for s in c.get("calls",[]): walk(s, depth+1)
walk(r)
open("scratch/compound-accrue-trace.json","w").write(json.dumps(r))
