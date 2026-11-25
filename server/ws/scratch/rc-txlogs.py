"""Summarize a tx's logs. usage: rc-txlogs.py <chain> <txhash>"""
import json, os, sys, urllib.request
chain, tx = sys.argv[1], sys.argv[2]
url = os.environ['RPC_RELAY_URL'].rstrip('/') + '/' + chain + '?lane=research'
def rpc(m, p):
    body = json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': m, 'params': p}).encode()
    r = urllib.request.Request(url, data=body, headers={'content-type': 'application/json'})
    return json.loads(urllib.request.urlopen(r, timeout=30).read())['result']
t = rpc('eth_getTransactionByHash', [tx])
print('from', t['from'], 'to', t['to'], 'block', int(t['blockNumber'], 16))
print('input', t['input'][:330])
rc = rpc('eth_getTransactionReceipt', [tx])
T = '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
for l in rc['logs']:
    tp = l['topics']
    if tp and tp[0] == T and len(tp) == 3:
        print('Transfer', l['address'], '0x' + tp[1][-40:], '->', '0x' + tp[2][-40:], int(l['data'], 16) / 1e18)
    else:
        print('log', l['address'], tp[0] if tp else None, [x[-40:] for x in tp[1:]], l['data'][:130])
