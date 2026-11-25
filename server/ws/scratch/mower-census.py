import json, urllib.request, os, collections
URL=os.environ['RPC_RELAY_URL']; LANE=os.environ.get('RPC_LANE') or 'research'
def rpc(method, params, chain='ethereum', lane=None):
    body=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    req=urllib.request.Request(f"{URL}/{chain}?lane={lane or LANE}", data=body, headers={'content-type':'application/json'})
    return json.loads(urllib.request.urlopen(req, timeout=60).read())['result']
HEAD=26372987
CVXCRV="0x62b9c7356a2dc64a1969e19c23e4f579f9810aa7"
Z0="0x"+"0"*64
txs=[]
for i in range(3):
    to=HEAD-i*10000; frm=to-9999
    logs=rpc("eth_getLogs",[{"address":CVXCRV,"topics":[None,Z0],"fromBlock":hex(frm),"toBlock":hex(to)}])
    print(f"window {frm}-{to}: {len(logs)} mints")
    txs += [l['transactionHash'] for l in logs]
txs=list(dict.fromkeys(txs))
print("unique txs:", len(txs))
senders=collections.Counter(); calldata={}
for h in txs[:40]:
    t=rpc("eth_getTransactionByHash",[h])
    if t:
        senders[t['from']]+=1
        calldata.setdefault(t['input'][:10], 0); calldata[t['input'][:10]]+=1
print("senders:", senders.most_common())
print("selectors:", calldata.most_common(10))
json.dump(txs, open('scratch/mower-mint-txs.json','w'))
