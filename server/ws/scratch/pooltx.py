import json, urllib.request, os
URL=os.environ['RPC_RELAY_URL']
def rpc(method, params, chain='ethereum', lane='research'):
    body=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    req=urllib.request.Request(f"{URL}/{chain}?lane={lane}", data=body, headers={'content-type':'application/json'})
    d=json.loads(urllib.request.urlopen(req, timeout=90).read())
    return d.get('result')
txs=json.load(open('scratch/pool-out-txs.json'))
import collections
info={}
for h in txs:
    t=rpc("eth_getTransactionByHash",[h])
    if t['to']=="0xcf50b810e57ac33b91dcf525c6ddd9881b139332" and t['input'][:10]=='0xa4698feb':
        print('direct pool tx', h, 'from', t['from'], 'input', t['input'][:74], 'block', int(t['blockNumber'],16))
        blk=t['blockNumber']; break
# receipts of that block
r=rpc("eth_getBlockReceipts",[blk])
for rec in r:
    logs=[l for l in rec['logs']]
    for l in logs:
        print('  log topic0', l['topics'][0], 'addr', l['address'], 'txmatch', l['transactionHash']==h)
