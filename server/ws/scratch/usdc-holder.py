import json, urllib.request, os
url = os.environ['RPC_RELAY_URL'] + '/ethereum'
lane = os.environ.get('RPC_LANE', 'research')

def rpc(m, p):
    b = json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': m, 'params': p}).encode()
    r = urllib.request.urlopen(urllib.request.Request(url + '?lane=' + lane, data=b,
        headers={'content-type': 'application/json'}), timeout=60)
    d = json.load(r)
    if 'error' in d:
        raise SystemExit('rpc error: %s' % d['error'])
    return d['result']

USDC = '0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48'
TRANSFER = '0xddf252ad1be2c89b69c2b068fc378daa952ba7f4ac15760e118f2a154185569d'
blk = int(rpc('eth_blockNumber', []), 16)
logs = rpc('eth_getLogs', [{'fromBlock': hex(blk - 400), 'toBlock': hex(blk),
                            'address': USDC, 'topics': [TRANSFER]}])
print('head', blk, 'transfer logs', len(logs))
cands = sorted({l['topics'][1][26:] for l in logs})
for c in cands[:10]:
    bal = rpc('eth_call', [{'to': USDC, 'data': '0x70a08231' + c}, 'latest'])
    print(c, int(bal, 16) / 1e6)
