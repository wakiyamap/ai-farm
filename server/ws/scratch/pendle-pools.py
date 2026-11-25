import json, urllib.request, os
URL=os.environ["RPC_RELAY_URL"]; LANE=os.environ.get("RPC_LANE","research")
def call(chain, method, params):
    body={"jsonrpc":"2.0","id":1,"method":method,"params":params}
    r=urllib.request.urlopen(URL.rstrip("/")+"/"+chain+"?lane="+LANE, json.dumps(body).encode(), timeout=30)
    j=json.loads(r.read())
    if "error" in j: return {"error": j["error"]}
    return j["result"]
FACT="0x27b1dacd74688af24a64bd3c9c1b143118740784"
SYS=["0x31853542da976400fb66278be7a09636aad332fc","0xa57854210b569aabf55f8f99ad16705053e563b8",
     "0xc994861c0041d88addf99fd136fe94fdd9b634bf","0x1593d2b64365bed60caf54ecb7448171214e33c1",
     "0xca7a1774d50c2bf3ebdeb205bf72390743752231","0x711fbd23db52f49993d5c460946bd3cba2424ff3",
     "0x6689ebb7b8b0da99befdf6974310d733f6166e40","0xf3135b0ba174b502ac22a6a9cfe996542a7e353f"]
out={}
head=int(call("ethereum","eth_blockNumber",[]),16)
out["head"]=head
sel_getPoolBySy="0xb61ff64b"+ "afb798af36b9bb3866a3460ee5e1e09eccc4934730b20ef024ae28fe"[8:]
# build selector via cast keccak outputs pasted:
sels={"getPoolBySy":"0xb61ff64b","scale":"0xf51e181a"}
def sel(name): return sels[name]
for sy in SYS:
    d=call("ethereum","eth_call",[{"to":FACT,"data":sel_getPoolBySy+"000000000000000000000000"+sy[2:]},"latest"])
    out.setdefault("poolBySy",{})[sy]= d if isinstance(d,str) else d
out["scale"]=call("ethereum","eth_call",[{"to":FACT,"data":sels["scale"]},"latest"])
# NewPool scan
tp={"5fb87e20":"NewPool(addr,bytes32,address)","4b162a6a":"NewPool(addr,bytes32,uint40)"}
for t0 in tp:
    topic="0x"+t0+"0000000000000000000000000000000000000000000000000000000000000000"[8:] if False else "0x"+t0+"8c69994106560188cd268396ca1e88555c13cf6540bc59d0f56b3c5b" if t0=="5fb87e20" else "0x"+t0+"cb830224595c53ea6a405fdc506632d4018d8d3b1fca9971"
    r=call("ethereum","eth_getLogs",[{"address":FACT,"topics":[topic],"fromBlock":hex(head-40000),"toBlock":hex(head)}])
    out.setdefault("newpool",{})[t0]= r if isinstance(r,list) else r
json.dump(out,open("scratch/pendle-pools.json","w"),indent=1)
print(json.dumps(out,indent=1)[:2000])
