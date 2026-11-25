import json, urllib.request
RELAY="http://127.0.0.1:8545"; CHAIN="arbitrum"
T0="0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
def rpc(method,params,show=False):
    body=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params})
    req=urllib.request.Request(f"{RELAY}/{CHAIN}?lane=research",data=body.encode(),headers={"content-type":"application/json"})
    r=json.load(urllib.request.urlopen(req,timeout=60))
    if "error" in r: print("ERR",json.dumps(r["error"])[:220]); return ("ERR",None)
    return ("OK",r["result"])
st,head=rpc("eth_blockNumber",[]); head=int(head,16)
st,logs=rpc("eth_getLogs",[{"fromBlock":hex(head-2000),"toBlock":hex(head),"topics":[T0]}])
print("topic-only Transfer last2000:",st,len(logs or []))
