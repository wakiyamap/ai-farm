import json, urllib.request, os, collections
URL=os.environ['RPC_RELAY_URL']
def rpc(method, params, chain='ethereum', lane='research'):
    body=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    req=urllib.request.Request(f"{URL}/{chain}?lane={lane}", data=body, headers={'content-type':'application/json'})
    d=json.loads(urllib.request.urlopen(req, timeout=90).read())
    if 'result' not in d: print('ERR', json.dumps(d)[:200])
    return d.get('result')
CRV="0xd533a949740bb3306d119cc777fa900ba034cd52"; POOLT="0x"+"0"*24+"cf50b810e57ac33b91dcf525c6ddd9881b139332"
HEAD=26372987
rec=collections.Counter(); txs=[]; tot=0
for i in range(6):
    to=HEAD-i*10000; frm=to-9999
    logs=rpc("eth_getLogs",[{"address":CRV,"topics":[None,POOLT],"fromBlock":hex(frm),"toBlock":hex(to)}])
    if logs is None: continue
    tot+=len(logs)
    for l in logs:
        r=l['topics'][2][26:]; rec["0x"+r]+=1
        txs.append(l['transactionHash'])
print("pool-out CRV events, 60k blocks:", tot, "recipients:", rec.most_common(12))
txs=list(dict.fromkeys(txs)); print("unique txs:", len(txs))
sel=collections.Counter(); tos=collections.Counter()
import concurrent.futures
def fetch(h):
    return rpc("eth_getTransactionByHash",[h])
with concurrent.futures.ThreadPoolExecutor(8) as ex:
    for t in ex.map(fetch, txs):
        tos[t['to']]+=1; sel[t['input'][:10]]+=1
print("tos:", tos.most_common(8)); print("sels:", sel.most_common(8))
json.dump(txs[:20], open('scratch/pool-out-txs.json','w'))
