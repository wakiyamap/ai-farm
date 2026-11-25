import json, os, urllib.request, concurrent.futures, collections, datetime

base = os.environ['RPC_RELAY_URL'].rstrip('/') + '/arbitrum?lane=research'
logs = json.load(open('scratch/mycelium-v2-logs.json'))['result']

def rpc(method, params):
    body = json.dumps({'jsonrpc':'2.0','id':1,'method':method,'params':params}).encode()
    req = urllib.request.Request(base, body, {'content-type':'application/json'})
    ans = json.load(urllib.request.urlopen(req, timeout=30))
    if 'error' in ans: raise RuntimeError(ans['error'])
    return ans['result']

def row(log):
    block = rpc('eth_getBlockByNumber',[log['blockNumber'],False])
    tx = rpc('eth_getTransactionByHash',[log['transactionHash']])
    receipt = rpc('eth_getTransactionReceipt',[log['transactionHash']])
    return {'block':int(log['blockNumber'],16),'ts':int(block['timestamp'],16),
            'pool':'0x'+log['topics'][1][-40:],'recipient':'0x'+log['topics'][2][-40:],
            'tx':log['transactionHash'],'from':tx['from'],'index':int(log['transactionIndex'],16),
            'reward_usdce':int(log['data'],16)/1e6,'gas_used':int(receipt['gasUsed'],16),
            'gas_price_gwei':int(receipt['effectiveGasPrice'],16)/1e9,
            'base_fee_gwei':int(block['baseFeePerGas'],16)/1e9,
            'priority_gwei':(int(receipt['effectiveGasPrice'],16)-int(block['baseFeePerGas'],16))/1e9,
            'gas_eth':int(receipt['gasUsed'],16)*int(receipt['effectiveGasPrice'],16)/1e18}

with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
    rows=sorted(pool.map(row,logs),key=lambda r:r['block'])
cut=int(datetime.datetime(2026,11,15,14,10,tzinfo=datetime.timezone.utc).timestamp())
rows=[r for r in rows if r['ts']>=cut]
json.dump(rows,open('scratch/mycelium-v2-measured.json','w'),indent=2)
for addr, rr in collections.defaultdict(list,((k,[x for x in rows if x['pool']==k]) for k in set(x['pool'] for x in rows))).items():
    print(addr,'count',len(rr),'reward',round(sum(x['reward_usdce'] for x in rr),6),
          'gas_eth',round(sum(x['gas_eth'] for x in rr),7),
          'actors',collections.Counter(x['recipient'] for x in rr),'indices',collections.Counter(x['index'] for x in rr))
    for x in rr: print(x['block'],x['ts'],x['tx'],x['recipient'],x['reward_usdce'],x['gas_used'],x['gas_price_gwei'])
