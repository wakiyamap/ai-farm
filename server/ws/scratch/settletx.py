import json, urllib.request, os
RL = os.environ['RPC_RELAY_URL'] + '/ethereum?lane=research'
hashes = [
 '0x3bd338b94dfb6790226262f7cf796ce45d003c4f318960c63f2ba7c86a255a39',
 '0x3733f5b33151462413c101088b6dfb90084e9322dc90ae7b2b18108f179ace87',
 '0x86a8e2483ff0da504f174843dab41647b6dc490aaef14abe5184ac5af5d22fd1',
 '0x432fac320e4dc8ccac97ec771cd6237c6738a7bf8e479bacea61c126d46f1741',
 '0x9d8c84b603395fa18926913c517996bdd5da57a604f268a0107a0e746f762033',
 '0x0af25674db4a10097cce8f7df03ccd79fa02b2a03791497751ae471fbdf6a33a',
 '0x7971fe57befc6c49ca10e492a517f31434d3fc96b1d9cb89a603ab23019d7b52',
]
def post(method, params):
    req = json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    return json.loads(urllib.request.urlopen(urllib.request.Request(RL, req, headers={'content-type':'application/json'}), timeout=30).read())['result']
for h in hashes:
    t = post('eth_getTransactionByHash', [h])
    print(h[:14], 'from', t['from'], 'to', t['to'], 'gas', t['gas'], 'gasPrice', int(t['gasPrice'],16), 'val', int(t['value'],16), 'dataSel', (t.get('input') or t.get('data') or '0x')[:10])
