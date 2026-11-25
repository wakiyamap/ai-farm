import json, urllib.request
RELAY="http://127.0.0.1:8545"; CHAIN="ethereum"; LANE="research"
TOKEN="0x2f714d7b9a035d4ce24af8d9b6091c07e37f43fb"
T0="0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
ZERO="0x"+"0"*64
def rpc(method,params,lane=LANE):
    body=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params})
    req=urllib.request.Request(f"{RELAY}/{CHAIN}?lane={lane}",data=body.encode(),headers={"content-type":"application/json"})
    r=json.load(urllib.request.urlopen(req,timeout=60))
    if "error" in r: return ("ERR",r["error"])
    return ("OK",r["result"])
st,head=rpc("eth_blockNumber",[]); head=int(head,16); print("head",head)
st,res=rpc("eth_getStorageAt",[TOKEN,"0x360894a13ba1a3210667c82834401656197bf257197d9a85c976912b37773876","latest"])
print("impl slot ->",st,res)
for name,data in [("name","0x06fdde03"),("symbol","0x95d89b02"),("decimals","0x313fa5"),("totalSupply","0x18160ddd")]:
    st,res=rpc("eth_call",[{"to":TOKEN,"data":data},"latest"])
    print(name,st,res[:200] if res else res)
frm=hex(head-30000); st,logs=rpc("eth_getLogs",[{"fromBlock":frm,"toBlock":hex(head),"address":[TOKEN],"topics":[T0,ZERO]}])
print("mint logs",st,len(logs or []))
mint_txs=[(l['transactionHash'],l['blockNumber'],l['logIndex']) for l in (logs or [])]
json.dump(mint_txs,open("scratch/node88-mints.json","w"))
recip=[int(l['topics'][2],16) for l in (logs or [])]
recips={f"0x{r:040x}" for r in recip}
print("distinct recipients",len(recips),sorted(recips)[:5])
blocks=[int(l['blockNumber'],16) for l in (logs or [])]
if blocks: print("mint blocks min/max",min(blocks),max(blocks),"per-day",round(len(blocks)/(head-min(blocks))/160,2))
