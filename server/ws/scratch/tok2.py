import json, urllib.request, os
RL = os.environ['RPC_RELAY_URL'] + '/ethereum?lane=research'
def call(to, data):
    req = json.dumps({"jsonrpc":"2.0","id":1,"method":"eth_call","params":[{"to":to,"data":data},"latest"]}).encode()
    r = json.loads(urllib.request.urlopen(urllib.request.Request(RL, req, headers={'content-type':'application/json'}), timeout=30).read())
    return r.get('result') or r.get('error')
for t in ['0x320623b8e4ff03373931769a31fc52a4e78b5d70','0xa0d69e286b938e21cbf7e51d71f6a4c8918f482f','0xe72b141df173b999ae7c1adcbf60cc9833ce56a8']:
    for sel,desc in [('0x06fdde03','symbol'),('0x95d09600','decimals'),('0x6edde7d3','decimals? no')]:
        pass
    print(t)
    print(' symbol:', call(t,'0x06fdde03'))
    print(' decimals:', call(t,'0x95d09600'))
    print(' name:', call(t,'0x06fdde03'))
