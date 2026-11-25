import json, urllib.request, os
URL=os.environ["RPC_RELAY_URL"]; LANE=os.environ.get("RPC_LANE","research")
def call(method, params):
    body={"jsonrpc":"2.0","id":1,"method":method,"params":params}
    r=urllib.request.urlopen(URL.rstrip("/")+"/ethereum?lane="+LANE, json.dumps(body).encode(), timeout=30)
    j=json.loads(r.read())
    if "error" in j: return {"error": j["error"]}
    return j["result"]
V6="0x6d247b1c044fA1E22e6B04fA9F71Baf99EB29A9f"
CANDS={"6fcf753f":"0x6fcf753f2c67b83f7b09746bbc4fa0047b35d050"}
FACTS=["0x6d247b1c044fA1E22e6B04fA9F71Baf99EB29A9f","0xc78bc588e970501432b2583ec1b6d2f4509b3b55"]
SYS=["0x31853542da976400fb66278be7a09636aad332fc","0x1593d2b64365bed60caf54ecb7448171214e33c1"]
GP="b61ff64bafb798af36b9bb3866a3460ee5e1e09eccc4934730b20ef024ae28fe"
RS="e3487d8f0000000000000000000000000000000000000000000000000000000000000000"
out={}
for f in FACTS:
    for sy in SYS:
        out.setdefault("poolBySy",{})[f+"/"+sy[:10]]=call("eth_call",[{"to":f,"data":"0x"+GP[0:8]+"0"*24+sy[2:]},"latest"])
    out.setdefault("reserves",{})[f]=call("eth_call",[{"to":f,"data":"0x"+"e3487d8f"+"0"*24+"3c9f23806a18237664d9a467971688030a4402047b42d5c69a37019361100600"[48:]},"latest"]) # placeholder USDe addr replaced below
json.dump(out,open("scratch/pendle-pools3-pre.json","w"),indent=1)
# factory raw logs around creation blocks for each candidate factory
logs={}
for f in FACTS:
    r=call("eth_getLogs",[{"address":f,"fromBlock":hex(26354700),"toBlock":hex(26354850)}])
    logs[f]=r if isinstance(r,list) else r
out["factory_logs"]=logs
json.dump(out,open("scratch/pendle-pools3.json","w"),indent=1)
print(json.dumps(out,indent=1)[:2500])
