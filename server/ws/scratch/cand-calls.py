import json, urllib.request, os, collections
URL=os.environ['RPC_RELAY_URL']
def rpc(method, params, chain='ethereum', lane='research'):
    body=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    req=urllib.request.Request(f"{URL}/{chain}?lane={lane}", data=body, headers={'content-type':'application/json'})
    d=json.loads(urllib.request.urlopen(req, timeout=120).read())
    return d.get('result', 'ERR:'+str(d.get('error',{}).get('message')))
CAND="0xb576491f1e6e5e62f1d8f26062ee822b40b0e0d4"; CRV="0xd533a949740bb3306d119cc777fa900ba034cd52"
HEAD=26372987; T2="0x"+"0"*24+CAND[2:]
txs=set()
for i in range(4):
    to=HEAD-i*20000; frm=to-19999
    logs=rpc("eth_getLogs",[{"address":CRV,"topics":[None,None,T2],"fromBlock":hex(frm),"toBlock":hex(to)}])
    if not logs: continue
    for l in logs: txs.add(l['transactionHash'])
print('txs with CRV->candidate in 80k blocks:', len(txs))
sels=collections.Counter(); frm=collections.Counter()
import concurrent.futures
def fetch(h): return rpc("eth_getTransactionByHash",[h])
with concurrent.futures.ThreadPoolExecutor(6) as ex:
    for t in ex.map(fetch, list(txs)[:25]):
        sels[t['input'][:10] if t['to']==CAND else (t['to'],t['input'][:10])]+=1
        frm[t['from']]+=1
print('to==cand selectors:', [k for k,v in sels.most_common(8)])
print('callers:', frm.most_common(6))
