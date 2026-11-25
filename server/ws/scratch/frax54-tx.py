import json,urllib.request,os
url=os.environ["RPC_RELAY_URL"]+"/ethereum?lane=research"
def rq(method,params):
    d={"jsonrpc":"2.0","id":1,"method":method,"params":params}
    req=urllib.request.Request(url,data=json.dumps(d).encode(),headers={"content-type":"application/json"})
    return json.loads(urllib.request.urlopen(req,timeout=20).read())["result"]
def call(to,sig):
    r=rq("eth_call",[{"to":to,"data":sig},"latest"])
    return r
out={}
# asset of the two remaining pairs
for a in ["0xdbe88dbac39263c47629ebba02b3ef4cf0752a72","0x66bf36dba79d4606039f04b32946a260bcd3ff52"]:
    out["asset_"+a[:6]]=call(a,"0x38d52e0f")
# tx + block for the batch tx and the two singles
txs=["0x5cb279a061d8d75b0dc6ad5e83f9da8fec59bc4b22b9755837a5c0869a7b4018",
     "0xc23e507e41","0x9e854a65ad"]
for h in ["0x5cb279a061d8d75b0dc6ad5e83f9da8fec59bc4b22b9755837a5c0869a7b4018"]:
    t=rq("eth_getTransactionByHash",[h])
    out["gasUsed"]=int(t["gasUsed"],16); out["to"]=t["to"]; out["from"]=t["from"]
    out["input_len"]=len(t["input"])//2
    bn=int(t["blockNumber"],16)
    blk=rq("eth_getBlockByNumber",["0x%x"%bn,False])
    out["basefee"]=int(blk["baseFeePerGas"],16)
print(json.dumps(out,indent=1))
