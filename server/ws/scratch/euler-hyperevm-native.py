import json
import os
import urllib.request
from pathlib import Path

root = Path('/srv/farm/ws/scratch')
files = [root / f'euler-hyperevm-receipt-{i}.json' for i in range(4)]
files.insert(1, root / 'euler-hyperevm-receipt.json')
url = os.environ['RPC_RELAY_URL'].rstrip('/') + '/hyperevm'
seq = 0

def rpc(method, params):
    global seq
    seq += 1
    request = urllib.request.Request(url, data=json.dumps({'jsonrpc':'2.0','id':seq,'method':method,'params':params}).encode(), headers={'Content-Type':'application/json'})
    data = json.load(urllib.request.urlopen(request, timeout=60))
    if 'error' in data: raise RuntimeError(data['error'])
    return data['result']

for path in files:
    r = json.loads(path.read_text())['result']
    h = r['transactionHash']
    tx = rpc('eth_getTransactionByHash', [h])
    bn = int(r['blockNumber'], 16)
    liqs = {l['topics'][1][-40:].lower() for l in r['logs'] if l['topics'][0].startswith('0x8246cc71')}
    addrs = {tx['from'].lower(), *('0x' + x for x in liqs)}
    changes = {}
    for addr in addrs:
        p = int(rpc('eth_getBalance', [addr, hex(bn - 1)]), 16)
        c = int(rpc('eth_getBalance', [addr, hex(bn)]), 16)
        changes[addr] = round((c-p) / 1e18, 9)
    gas_hype = int(r['gasUsed'],16) * int(r['effectiveGasPrice'],16) / 1e18
    print(h, 'block', bn, 'from', tx['from'], 'liq', liqs, 'native_delta_hype', changes, 'gas_hype', round(gas_hype, 9))
