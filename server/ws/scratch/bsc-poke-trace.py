import json, urllib.request, os
RELAY = os.environ["RPC_RELAY_URL"]
def rpc(method, params, chain="bsc", lane="research"):
    body = json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    req = urllib.request.Request(f"{RELAY}/{chain}?lane={lane}", data=body,
        headers={"content-type":"application/json"})
    r = json.loads(urllib.request.urlopen(req, timeout=120).read())
    if "error" in r: print("ERR", r["error"]); return None
    return r["result"]
def summarize(txh):
    t = rpc("debug_traceTransaction", [txh, {"tracer":"callTracer"}])
    if t is None: return
    def walk(f, d=0):
        ai = f.get("address", f.get("from"))
        print("  "*d, f.get("type"), ai, "->", f.get("to"), "val", f.get("value","0x0")[:8] if isinstance(f.get("value"),str) else f.get("value","0"), "gas", f.get("gasUsed"), "err", f.get("error",{}).get("errorCode","") if isinstance(f.get("error"),dict) else f.get("errorMessage",""))
        for s in f.get("calls", []): walk(s, d+1)
    walk(t)
    return t
print("== Claimed1 trace")
t = summarize("0x7b783e74fc64268f90003115ca863677de77eee4bcafd86eb69f6e1b9ce5d3f8")
json.dump(t, open("scratch/bsc-trace-claimed1.json","w"))
