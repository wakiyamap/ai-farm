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
st,head=rpc("eth_blockNumber",[]); head=int(head,16)
st,code=rpc("eth_getCode",[TOKEN,"latest"])
b=code[2:]
print("proxy tail last 120 bytes hex:", b[-240:])
# try last 10 bytes of a minimal proxy = impl addr often near end
print("tail-20:", b[-40:])
# control: address-only last 3000 blocks
st,logs=rpc("eth_getLogs",[{"fromBlock":hex(head-3000),"toBlock":hex(head),"address":[TOKEN]}])
print("control addr-only last3000:",st,len(logs or []))
# mint filter same window
st,logs=rpc("eth_getLogs",[{"fromBlock":hex(head-3000),"toBlock":hex(head),"address":[TOKEN],"topics":[T0,ZERO]}])
print("mint-filter last3000:",st,len(logs or []))
# all transfers last 3000 blocks with T0 only
st,logs=rpc("eth_getLogs",[{"fromBlock":hex(head-3000),"toBlock":hex(head),"address":[TOKEN],"topics":[T0]}])
print("T0-only last3000:",st,len(logs or []))
if logs:
    t1=set(l['topics'][1][-8:] if len(l['topics'])>1 else '-' for l in logs)
    print("sample topic1 tails:", list(t1)[:10])
