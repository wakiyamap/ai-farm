import json, urllib.request
RELAY="http://127.0.0.1:8545"; CHAIN="ethereum"
TOKEN="0x2f714d7b9a035d4ce24af8d9b6091c07e37f43fb"
IMPL="0x41d0b9DFbF915A77E6db1c1880C4d3B4F27A9B77"
SLOT="0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc"
def rpc(method,params):
    body=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params})
    req=urllib.request.Request(f"{RELAY}/{CHAIN}?lane=research",data=body.encode(),headers={"content-type":"application/json"})
    r=json.load(urllib.request.urlopen(req,timeout=60))
    if "error" in r: return ("ERR",json.dumps(r["error"])[:120])
    return ("OK",r["result"])
st,res=rpc("eth_getStorageAt",[TOKEN,SLOT,"latest"]); print("slot",st,res)
st,code=rpc("eth_getCode",[IMPL,"latest"]); print("impl code bytes",st,(len(code[2:])//2 if st=="OK" else code))
st,head=rpc("eth_blockNumber",[]); head=int(head,16)
T0="0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"; ZERO="0x"+"0"*64
mints=[]
for k in range(6):
    w=10000*(2**min(k,2))  # 10k,10k,10k,40k,40k,40k... simple: pages 10k each x 8
    frm=hex(head-10000*(k+1)); to=hex(head-10000*k)
    st,logs=rpc("eth_getLogs",[{"fromBlock":frm,"toBlock":to,"address":[TOKEN],"topics":[T0,ZERO]}])
    n=len(logs) if st=="OK" else st
    print(f"window {frm}..{to}: mints",st,n)
    if st=="OK" and logs:
        mints=[(l['transactionHash'],l['blockNumber']) for l in logs]; break
json.dump(mints,open("scratch/node88-lastmints.json","w"))
