import json, os, urllib.request
RELAY = os.environ["RPC_RELAY_URL"]
def rpc(method, params, lane="research"):
    req = urllib.request.Request(f"{RELAY}/ethereum?lane={lane}",
        data=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode(),
        headers={"content-type":"application/json"})
    for a in range(3):
        try:
            with urllib.request.urlopen(req, timeout=120) as r: d = json.loads(r.read())
            if "error" in d: raise RuntimeError(str(d["error"])[:150])
            return d["result"]
        except Exception as e:
            if a==2: raise
            print("retry:", str(e)[:120])
def call(to, data):
    return rpc("eth_call",[{"from":"0x"+"0"*40,"to":to,"data":data},"latest"])
TRANSFER="0xddf252ad1be2c89b69c2b89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
TRANSFER="0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
YT0="0xaa79d8f17776adeaa316c5411b72e8b0057d064974fa8748f32492ecaa22ecd1"
FACTS=["0x273b4bfa3bb30fe8f32c467b5f0046834557f072","0x35a338522a435d46f77be32c70e215b813d0e3ac","0x3e6eba46abc5ab18ed95f6667d8b2fd4020e4637"]
head=int(rpc("eth_blockNumber",[]),16)
out={"head":head}
# 1) all PTs maturing 26NOV2026 from yield factories over last ~120k blocks
exp="0x"+"{:0>64x}".format(1795651200)
logs=rpc("eth_getLogs",[{"address":FACTS,"topics":[YT0,None,None,exp],"fromBlock":hex(head-120000),"toBlock":hex(head)}])
nov=[]
for lg in logs:
    sy="0x"+"0"*len(lg['topics'][1][2:]-40)+lg['topics'][1][-40:]; pt="0x"+lg['topics'][2][-40:]; 
    nov.append({"sy":sy,"pt":pt,"blk":int(lg['blockNumber'],16)})
out["pts_26nov"]=nov
# 2) pools: SY transfers -> candidate to-addresses (pools hold SY), new cohort SYs
SY8=["0xca7a1774d50c2bf3ebdeb205bf72390743752231","0x711fbd23db52f49993d5c460946bd3cba2424ff3","0x6689ebb7b8b0da99befdf6974310d733f6166e40","0xf3135b0ba174b502ac22a6a9cfe996542a7e353f","0x31853542da976400fb66278be7a09636aad332fc","0xa57854210b569aabf55f8f99ad16705053e563b8","0xc994861c0041d88addf99fd136fe94fdd9b634bf","0x1593d2b64365bed60caf54ecb7448171214e33c1"]
addrs={}
for sy in SY8+ [n["sy"] for n in nov]:
    lg2=rpc("eth_getLogs",[{"address":[sy],"topics":[TRANSFER,None],"fromBlock":hex(head-30000),"toBlock":hex(head)}])
    tos={}
    for l in lg2:
        to="0x"+l['topics'][2][-40:]
        tos[to]=tos.get(to,0)+int(l['data'],16)
    addrs[sy]={"n_logs":len(lg2),"tos":sorted(tos.items(),key=lambda kv:-kv[1])[:6]}
out["sy_transfers"]=addrs
json.dump(out,open("scratch/pendle-pool-find.json","w"),indent=1)
print(json.dumps(out,indent=1)[:2500])
