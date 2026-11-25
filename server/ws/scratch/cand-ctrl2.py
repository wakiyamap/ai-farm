import json, urllib.request, os, collections
URL=os.environ['RPC_RELAY_URL']
def rpc(method, params, chain='ethereum', lane='research'):
    body=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    req=urllib.request.Request(f"{URL}/{chain}?lane={lane}", data=body, headers={'content-type':'application/json'})
    d=json.loads(urllib.request.urlopen(req, timeout=120).read())
    return d.get('result', 'ERR:'+str(d.get('error',{}).get('message')))
CAND="0xb576491f1e6e5e62f1d8f26062ee822b40b0e0d4"; CRV="0xd533a949740bb3306d119cc777fa900ba034cd52"
HEAD=26372987
def T2(a): return "0x"+"0"*24+a[2:]
logs=rpc("eth_getLogs",[{"address":CRV,"topics":[None,None,T2(CAND)],"fromBlock":hex(HEAD-60000),"toBlock":hex(HEAD)}])
print('cand receives (3-slot topic filter):', len(logs) if logs is not None else logs)
if logs:
    txs=sorted({l['transactionHash'] for l in logs})
    t=rpc("eth_getTransactionByHash",[txs[0]])
    print('sample tx', t['from'],'->',t['to'], t['input'][:10])
