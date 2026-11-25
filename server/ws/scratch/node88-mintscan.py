import json, urllib.request
RELAY="http://127.0.0.1:8545"; CHAIN="ethereum"
TOKEN="0x2f714d7b9a035d4ce24af8d9b6091c07e37f43fb"
T0="0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"; ZERO="0x"+"0"*64
def rpc(method,params):
    body=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params})
    req=urllib.request.Request(f"{RELAY}/{CHAIN}?lane=research",data=body.encode(),headers={"content-type":"application/json"})
    r=json.load(urllib.request.urlopen(req,timeout=60))
    if "error" in r: return ("ERR",json.dumps(r["error"])[:120])
    return ("OK",r["result"])
st,head=rpc("eth_blockNumber",[]); head=int(head,16)
found=None
for k in range(10):
    frm=hex(head-100000*(k+2)); to=hex(head-100000*(k+1))
    st,logs=rpc("eth_getLogs",[{"fromBlock":frm,"toBlock":to,"address":[TOKEN],"topics":[T0,ZERO]}])
    n=len(logs) if st=="OK" else st
    print(f"window {frm}..{to}: mints",st,n)
    if st=="OK" and logs:
        found=(frm,to,[(l['transactionHash'],l['blockNumber']) for l in logs][-5:])
        break
print("FOUND:",found)
