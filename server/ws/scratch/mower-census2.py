import json, urllib.request, os, collections
URL=os.environ['RPC_RELAY_URL']
def rpc(method, params, chain='ethereum', lane='research'):
    body=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    req=urllib.request.Request(f"{URL}/{chain}?lane={lane}", data=body, headers={'content-type':'application/json'})
    return json.loads(urllib.request.urlopen(req, timeout=90).read())['result']
txs=json.load(open('scratch/mower-mint-txs.json'))
by=[]
for h in txs:
    t=rpc("eth_getTransactionByHash",[h])
    by.append((h,t['from'],t['to'],t['input'][:10]))
sel=collections.Counter(x[3] for x in by)
print("selectors:", sel.most_common(10))
keep=[x for x in by if x[1]=="0xa88e98bbd2af6ddd642407cb5455f956f0c553f0"][:2]
sec=[x for x in by if x[1]=="0x7e79a8173b3f63395d6a59f8ca4af214c29d359b"][:2]
one=[x for x in by if x[1] not in ("0xa88e98bbd2af6ddd642407cb5455f956f0c553f0","0x7e79a8173b3f63395d6a59f8ca4af214c29d359b")]
json.dump({'keep':keep,'sec':sec,'one':one}, open('scratch/mower-bysender.json','w'), indent=1)
print(json.dumps({'keep':keep,'sec':sec,'one':one}, indent=1)[:800])
