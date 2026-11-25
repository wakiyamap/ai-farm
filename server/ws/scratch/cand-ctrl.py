import json, urllib.request, os
URL=os.environ['RPC_RELAY_URL']
def rpc(method, params, chain='ethereum', lane='research'):
    body=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    req=urllib.request.Request(f"{URL}/{chain}?lane={lane}", data=body, headers={'content-type':'application/json'})
    d=json.loads(urllib.request.urlopen(req, timeout=120).read())
    return d.get('result', 'ERR:'+str(d.get('error',{}).get('message')))
CAND="0xb576491f1e6e5e62f1d8f26062ee822b40b0e0d4"; CRV="0xd533a949740bb3306d119cc777fa900ba034cd52"; FEED="0x8014595f2ab54cd7c604b00e9fb932176fdc86ae"
HEAD=26372987
def t1(a): return "0x"+"0"*24+a[2:]
for name,a in [('control FeeDeposit receives',FEED),('candidate receives',CAND)]:
    logs=rpc("eth_getLogs",[{"address":CRV,"topics":[None,t1(a)],"fromBlock":hex(HEAD-60000),"toBlock":hex(HEAD)}])
    print(name, '->', len(logs) if logs is not None else logs)
