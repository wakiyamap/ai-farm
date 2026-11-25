import json, urllib.request, os
URL=os.environ['RPC_RELAY_URL']
def rpc(method, params, chain='ethereum', lane='research'):
    body=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    req=urllib.request.Request(f"{URL}/{chain}?lane={lane}", data=body, headers={'content-type':'application/json'})
    d=json.loads(urllib.request.urlopen(req, timeout=90).read())
    return d.get('result')
txs=json.load(open('scratch/pool-out-txs.json'))
POOL="0xcf50b810e57ac33b91dcf525c6ddd9881b139332"
h=None
for hx in txs:
    t=rpc("eth_getTransactionByHash",[hx])
    if t['to']==POOL and t['input'][:10]=='0xa4698feb':
        h=hx; blk=t['blockNumber']; print('tx',h,'from',t['from'],'input',t['input'][:4+64],'block',blk); break
r=rpc("eth_getBlockReceipts",[blk])
for rec in r:
    if rec['transactionHash']!=h: continue
    print('gasUsed', int(rec['gasUsed'],16), 'status', rec.get('status'))
    for l in rec['logs']:
        print('  log', l['address'][:12], l['topics'][0], len(l['topics']), 'data', l['data'][:26])
