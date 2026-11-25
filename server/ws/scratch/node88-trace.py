import json, urllib.request
RELAY="http://127.0.0.1:8545"; CHAIN="ethereum"
MINTER="0xc55c1ccd0a6028be42d37b72794d8433a3cfaaaa"
def rpc(method,params):
    body=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params})
    req=urllib.request.Request(f"{RELAY}/{CHAIN}?lane=research",data=body.encode(),headers={"content-type":"application/json"})
    r=json.load(urllib.request.urlopen(req,timeout=90))
    if "error" in r: return ("ERR",json.dumps(r["error"])[:200])
    return ("OK",r["result"])
h="0xd53232406a0389cc4b9b889c7018366b653cfcbc694c68751d39aec9389ae5c5"
st,res=rpc("debug_traceTransaction",[h,{"tracer":"prestateTracer","tracerConfig":{"diffMode":True}}])
print(st)
if st=="OK":
    pre=res.get("pre") or {}; post=res.get("post") or {}
    d={}
    for a in set(pre)|set(post):
        bal=lambda s: int((s.get(a) or {}).get("balance","0x0"),16)
        delta=bal(post)-bal(pre)
        if delta: d[a]=delta
    for a,v in d.items(): print(f"{a} delta {v/1e18:+.9f} ETH")
    json.dump({"pre":pre,"post":post},open("scratch/node88-prestate.json","w"))
else: print(res)
