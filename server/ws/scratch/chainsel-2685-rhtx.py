"""Inspect the big Robinhood captures: tx receipt emitters, the market oracle, logs of the oracle in the prior blocks."""
import json, urllib.request, sys
url = "https://rpc.mainnet.chain.robinhood.com"
def call(m, p):
    req = urllib.request.Request(url, data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": m, "params": p}).encode(),
                                 headers={"Content-Type": "application/json", "User-Agent": "farm-research/1"})
    j = json.load(urllib.request.urlopen(req, timeout=30))
    return j.get('result', j.get('error'))
d = json.load(open('chainsel-2685-rh-events.json'))
for blk in map(int, sys.argv[1:]):
    x = [e for e in d['events'] if e['block'] == blk][0]
    m = d['markets'][x['id']]
    print('==', blk, x['tx'], 'caller', x['caller'], 'borrower', x['borrower'], 'repaid', x['repaid'], 'seized', x['seized'], 'baddebt', x['baddebt'])
    print('market', m['syms'], 'oracle', m['oracle'], 'lltv', m['lltv'])
    tx = call('eth_getTransactionByHash', [x['tx']])
    print('tx from', tx['from'], 'to', tx['to'], 'input', tx['input'][:10], 'len', len(tx['input']))
    rc = call('eth_getTransactionReceipt', [x['tx']])
    print('emitters', [(l['address'], l['topics'][0][:10]) for l in rc['logs']])
    code = call('eth_getCode', [m['oracle'], 'latest'])
    print('oracle code bytes', (len(code) - 2) // 2)
    t0 = int(call('eth_getBlockByNumber', [hex(blk), False])['timestamp'], 16)
    print('capture ts', t0)
