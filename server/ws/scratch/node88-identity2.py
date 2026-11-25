import json, urllib.request
RELAY="http://127.0.0.1:8545"; CHAIN="ethereum"; LANE="research"
TOKEN="0x2f714d7b9a035d4ce24af8d9b6091c07e37f43fb"
T0="0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
ZERO="0x"+"0"*64
def rpc(method,params):
    body=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params})
    req=urllib.request.Request(f"{RELAY}/{CHAIN}?lane={LANE}",data=body.encode(),headers={"content-type":"application/json"})
    r=json.load(urllib.request.urlopen(req,timeout=60))
    if "error" in r: return ("ERR",json.dumps(r["error"])[:160])
    return ("OK",r["result"])
st,head=rpc("eth_blockNumber",[]); head=int(head,16); print("head",head)
st,code=rpc("eth_getCode",[TOKEN,"latest"]); print("code len",st,len((code or '')[2:])//2)
for name,data in [("symbol","0x95d89b02"),("decimals","0x313fa5"),("totalSupply","0x18160ddd"),("implementation","0x5c60da1b")]:
    st,res=rpc("eth_call",[{"to":TOKEN,"data":data},"latest"]); print(name,st,str(res)[:120])
frm=hex(head-30000)
st,logs=rpc("eth_getLogs",[{"fromBlock":frm,"toBlock":hex(head),"address":[TOKEN],"topics":[T0,ZERO]}])
logs = logs if st=="OK" and isinstance(logs,list) else []
print("mint logs",st,len(logs))
mint_txs=[(l['transactionHash'],l['blockNumber'],l['logIndex']) for l in logs]
json.dump(mint_txs,open("scratch/node88-mints.json","w"))
recips={}
for l in logs:
    r="0x"+l['topics'][2][-40:]; recips[r]=recips.get(r,0)+1
print("distinct recipients",len(recips), sorted(recips.items(), key=lambda x:-x[1])[:6])
blocks=[int(l['blockNumber'],16) for l in logs]
if blocks: print("span blocks",head-min(blocks),"mints/day",round(len(logs)/((head-min(blocks))/160),2))
