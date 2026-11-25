import json, urllib.request, re
RELAY="http://127.0.0.1:8545"; CHAIN="arbitrum"
A1="0xC2dA9d9EC6eaCAA33B8FcA11B7a0dEf8b1184491"; A2="0xa42232A9dD84409B3169092A5F34B55B4Fba7203"
def rpc(method,params):
    body=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params})
    req=urllib.request.Request(f"{RELAY}/{CHAIN}?lane=research",data=body.encode(),headers={"content-type":"application/json"})
    r=json.load(urllib.request.urlopen(req,timeout=60))
    if "error" in r: return ("ERR",json.dumps(r["error"])[:120])
    return ("OK",r["result"])
st,head=rpc("eth_blockNumber",[]); head=int(head,16)
for a in [A1,A2]:
    st,logs=rpc("eth_getLogs",[{"fromBlock":hex(head-1000000),"toBlock":hex(head),"address":[a]}])
    n=len(logs or []) if st=="OK" else st
    print(a,"logs/1M blocks(~11.6d):",st,n, (logs[0]['blockNumber'] if isinstance(logs,list) and logs else ''))
st,code=rpc("eth_getCode",[A1,"latest"]); b=code[2:]
print("A1 code hex:",b)
m=[x.group(1) for x in re.finditer("7f([0-9a-f]{64})",b)]
print("PUSH32 consts:",m)
