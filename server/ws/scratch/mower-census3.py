import json, urllib.request, os, collections
URL=os.environ['RPC_RELAY_URL']
def rpc(method, params, chain='ethereum', lane='research'):
    body=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    req=urllib.request.Request(f"{URL}/{chain}?lane={lane}", data=body, headers={'content-type':'application/json'})
    return json.loads(urllib.request.urlopen(req, timeout=90).read())['result']
HEAD=26372987
CVXCRV="0x62b9c7356a2dc64a1969e19c23e4f579f9810aa7"
Z0="0x"+"0"*64
txs=[]
for i in range(3):
    to=HEAD-i*10000; frm=to-9999
    logs=rpc("eth_getLogs",[{"address":CVXCRV,"topics":[None,Z0],"fromBlock":hex(frm),"toBlock":hex(to)}])
    txs += [l['transactionHash'] for l in logs]
txs=list(dict.fromkeys(txs))
by=[]
for h in txs:
    t=rpc("eth_getTransactionByHash",[h])
    by.append({'h':h,'from':t['from'],'to':t['to'],'sel':t['input'][:10],'block':int(t['blockNumber'],16)})
sel=collections.Counter(x['sel'] for x in by); print("selectors:", sel.most_common(10))
byfrom=collections.Counter(x['from'] for x in by); print("froms:", byfrom.most_common())
K="0xa88e98bbd2af6ddd642407cb5455f956f0c553f0"; S="0x7e79a8173b3f63395d6a59f8ca4af214c29d359b"
out={'keep':[x for x in by if x['from']==K][:2],'sec':[x for x in by if x['from']==S][:2],
     'one':[x for x in by if x['from'] not in (K,S)]}
json.dump(out, open('scratch/mower-bysender.json','w'), indent=1)
for k,v in out.items(): print(k, json.dumps(v)[:400])
