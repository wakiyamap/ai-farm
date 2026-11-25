import json, urllib.request, os
URL=os.environ["RPC_RELAY_URL"]; LANE=os.environ.get("RPC_LANE","research")
def call(method, params):
    body={"jsonrpc":"2.0","id":1,"method":method,"params":params}
    r=urllib.request.urlopen(URL.rstrip("/")+"/ethereum?lane="+LANE, json.dumps(body).encode(), timeout=30)
    j=json.loads(r.read())
    if "error" in j: return {"error": j["error"]}
    return j["result"]
FACT="0x27b1dacd74688af24a64bd3c9c1b143118740784"
H_GETPOOL="b61ff64bafb798af36b9bb3866a3460ee5e1e09eccc4934730b20ef024ae28fe"
H_SCALE="f51e181a89892dc7df34574dd16ec080ebebf00af15c07e334b5a3ded292b2d4"
SYS=["0x31853542da976400fb66278be7a09636aad332fc","0xa57854210b569aabf55f8f99ad16705053e563b8",
     "0xc994861c0041d88addf99fd136fe94fdd9b634bf","0x1593d2b64365bed60caf54ecb7448171214e33c1"]
out={}
for sy in SYS:
    out.setdefault("poolBySy",{})[sy]=call("eth_call",[{"to":FACT,"data":"0x"+H_GETPOOL[0:8]+"0"*24+sy[2:]},"latest"])
out["scale"]=call("eth_call",[{"to":FACT,"data":"0x"+H_SCALE[0:8]},"latest"])
# raw logs around pool creation blocks (no topic filter), factory only
r=call("eth_getLogs",[{"address":FACT,"fromBlock":hex(26354700),"toBlock":hex(26354850)}])
out["factory_logs"]=r if isinstance(r,list) else r
json.dump(out,open("scratch/pendle-pools2.json","w"),indent=1)
print(json.dumps(out,indent=1)[:3000])
