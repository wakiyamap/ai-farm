import json, urllib.request, re
RELAY="http://127.0.0.1:8545"; CHAIN="ethereum"
TOKEN="0x2f714d7b9a035d4ce24af8d9b6091c07e37f43fb"
def rpc(method,params):
    body=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params})
    req=urllib.request.Request(f"{RELAY}/{CHAIN}?lane=research",data=body.encode(),headers={"content-type":"application/json"})
    r=json.load(urllib.request.urlopen(req,timeout=60))
    if "error" in r: return ("ERR",json.dumps(r["error"])[:120])
    return ("OK",r["result"])
st,code=rpc("eth_getCode",[TOKEN,"latest"]); b=code[2:]
print(len(b)//2,"bytes")
# find 32-byte push constants: any 64-hex substring after 7f
for m in re.finditer("7f([0-9a-f]{64})", b): print("PUSH32:",m.group(1))
# storage slot reads
for m in re.finditer("(6?54|5f54)", b): pass
print("has 54 sloc at:",[m.start() for m in re.finditer("54", b)][:8])
print("full:\n", b)
