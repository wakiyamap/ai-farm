import json, urllib.request, os, collections
URL=os.environ['RPC_RELAY_URL']
def rpc(method, params, chain='ethereum', lane='research'):
    body=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    req=urllib.request.Request(f"{URL}/{chain}?lane={lane}", data=body, headers={'content-type':'application/json'})
    d=json.loads(urllib.request.urlopen(req, timeout=120).read())
    return d.get('result', 'ERR:'+str(d.get('error',{}).get('message')))
CAND="0xb576491f1e6e5e62f1d8f26062ee822b40b0e0d4"; CRV="0xd533a949740bb3306d119cc777fa900ba034cd52"
HEAD=26372987; T1="0x"+"0"*24+CAND[2:]
logs=rpc("eth_getLogs",[{"address":CRV,"topics":[None,T1],"fromBlock":hex(HEAD-60000),"toBlock":hex(HEAD)}])
print('cand receives (topic1 fix):', len(logs) if logs is not None else logs)
txs=list({l['transactionHash'] for l in logs}) if logs else []
import concurrent.futures
sels=collections.Counter(); frm=collections.Counter(); tos=collections.Counter()
def fetch(h): return rpc("eth_getTransactionByHash",[h])
if txs:
    with concurrent.futures.ThreadPoolExecutor(6) as ex:
        for t in ex.map(fetch, txs[:25]):
            tos[t['to']]+=1
            if t['to']==CAND: sels[t['input'][:10]]+=1
            frm[t['from']]+=1
    print('tos:', tos.most_common(5)); print('selectors on cand:', sels.most_common(6)); print('callers:', frm.most_common(5))
