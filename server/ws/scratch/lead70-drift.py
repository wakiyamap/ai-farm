import json, urllib.request
RELAY="http://127.0.0.1:8545"; CHAIN="arbitrum"
A1="0xC2dA9d9EC6eaCAA33B8FcA11B7a0dEf8b1184491"; A2="0xa42232A9dD84409B3169092A5F34B55B4Fba7203"
def rpc(method,params):
    body=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params})
    req=urllib.request.Request(f"{RELAY}/{CHAIN}?lane=research",data=body.encode(),headers={"content-type":"application/json"})
    r=json.load(urllib.request.urlopen(req,timeout=60))
    if "error" in r: return ("ERR",json.dumps(r["error"])[:120])
    return ("OK",r["result"])
st,head=rpc("eth_blockNumber",[]); head=int(head,16); print("arb head",head)
for a in [A1,A2]:
    st,code=rpc("eth_getCode",[a,"latest"]); n=(len(code[2:])//2 if st=="OK" else 0)
    st2,logs=rpc("eth_getLogs",[{"fromBlock":hex(head-100000),"toBlock":hex(head),"address":[a]}])
    print(a,"code",st,n,"logs/100k",st2,len(logs or []))
