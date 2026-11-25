import json, urllib.request, os
URL=os.environ['RPC_RELAY_URL']
def rpc(method, params, chain='ethereum', lane='research'):
    body=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    req=urllib.request.Request(f"{URL}/{chain}?lane={lane}", data=body, headers={'content-type':'application/json'})
    d=json.loads(urllib.request.urlopen(req, timeout=120).read())
    return d.get('result', 'ERR:'+str(d.get('error',{}).get('message')))
CAND="0xb576491f1e6e5e62f1d8f26062ee822b40b0e0d4"; CRV="0xd533a949740bb3306d119cc777fa900ba034cd52"
HEAD=26372987
def cnt(flt):
    logs=rpc("eth_getLogs",[flt]); return len(logs) if logs is not None else 'ERR '+str(logs)[:80]
wins=[(HEAD-60000,HEAD)]
for frm,to in wins:
    print('cand-receive census:', cnt({"address":CRV,"topics":[None,None,"0x"+"0"*24+CAND[2:]],"fromBlock":hex(frm),"toBlock":hex(to)}))
    print('control any CRV Transfer same window:', cnt({"address":CRV,"fromBlock":hex(frm),"toBlock":hex(to)}))
