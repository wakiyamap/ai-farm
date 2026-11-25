import json, urllib.request
RELAY="http://127.0.0.1:8545"; CHAIN="ethereum"
def rpc(method,params):
    body=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params})
    req=urllib.request.Request(f"{RELAY}/{CHAIN}?lane=research",data=body.encode(),headers={"content-type":"application/json"})
    r=json.load(urllib.request.urlopen(req,timeout=60))
    if "error" in r: return ("ERR",json.dumps(r["error"])[:160])
    return ("OK",r["result"])
txs=["0xd53232406a0389cc4b9b889c7018366b653cfcbc694c68751d39aec9389ae5c5","0x03974caca8bf6ab2d61fd9201a7e07bfdb977770d4a7e55ca9fce3c6e9dae9ae"]
for h in txs:
    st,tx=rpc("eth_getTransactionByHash",[h])
    if st=="OK":
        print(h[:12],"from",tx['from'],"to",tx['to'],"input",tx['input'][:16],"gasPrice",tx.get('gasPrice'),"value",int(tx['value'],16))
