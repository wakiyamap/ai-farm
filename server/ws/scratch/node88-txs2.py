import json, urllib.request
RELAY="http://127.0.0.1:8545"; CHAIN="ethereum"
TOKEN="0x2f714d7b9a035d4ce24af8d9b6091c07e37f43fb"
MINTER="0xc55c1ccd0a6028be42d37b72794d8433a3cfaaaa"
T0="0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"; ZERO="0x"+"0"*64
def rpc(method,params):
    body=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params})
    req=urllib.request.Request(f"{RELAY}/{CHAIN}?lane=research",data=body.encode(),headers={"content-type":"application/json"})
    r=json.load(urllib.request.urlopen(req,timeout=60))
    if "error" in r: return ("ERR",json.dumps(r["error"])[:160])
    return ("OK",r["result"])
st,code=rpc("eth_getCode",[MINTER,"latest"]); print("minter code bytes:",st,(len(code[2:])//2 if st=="OK" else code))
st,logs=rpc("eth_getLogs",[{"fromBlock":"0x18dcb3b","toBlock":"0x18f51db","address":[TOKEN],"topics":[T0,ZERO]}])
if st=="OK":
    for l in logs:
        rec="0x"+l['topics'][2][-40:]; amt=int(l['data'],16)/1e18
        print("mint blk",int(l['blockNumber'],16),"to",rec,"amt",f"{amt:.4f}","tx",l['transactionHash'][:16])
st,head=rpc("eth_blockNumber",[]); head=int(head,16)
# also check all transfers from minter window to measure token stream now: T0-only count in last 100k
st,logs=rpc("eth_getLogs",[{"fromBlock":hex(head-100000),"toBlock":hex(head),"address":[TOKEN],"topics":[T0]}])
print("T0 transfers last100k:",st,len(logs or []))
