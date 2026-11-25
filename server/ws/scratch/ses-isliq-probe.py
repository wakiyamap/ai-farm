import json, urllib.request, os
URL = os.environ['RPC_RELAY_URL'] + '/ethereum?lane=research'
MORPHO='0xbbbbbbbbbb9cc5e90e3b3af64bdaf62c37eeffcb'
ID='0xd2630c0ebf33ba83c82e8cd400a8e6345370238ca695ce58773b2d3e43de1b0a'
SEL_L='0x6eb71926'; SEL_H='0x67c572ea'
def call(data, tag):
    body=json.dumps({"jsonrpc":"2.0","id":1,"method":"eth_call","params":[{"to":MORPHO,"data":data}, f"0x{tag:x}" if isinstance(tag,int) else tag]}).encode()
    req=urllib.request.Request(URL, body, {'content-type':'application/json'})
    j=json.loads(urllib.request.urlopen(req, timeout=30).read())
    if 'error' in j: return ('ERR', json.dumps(j['error'])[:140])
    return j['result']
def probe(borrower, tag):
    d_l=SEL_L+ID[2:]+borrower[2:].rjust(64,'0')
    d_h=SEL_H+ID[2:]+borrower[2:].rjust(64,'0')
    return call(d_l,tag), call(d_h,tag)
tests=[
 ('0x14bcd9da052cdc6fe0b9446d5a616d5b7b4d4550', 26353673, 'whale C-1 of capture 26353674'),
 ('0x14bcd9da052cdc6fe0b9446d5a616d5b7b4d4550', 26345600, 'same borrower 8073 blocks early'),
 ('0x14bcd9da052cdc6fe0b9446d5a616d5b7b4d4550', 26353518, 'C-1 of small captures 26353519/20'),
 ('0xebf1ad18c0d4d1b3fe227f511f746a319a5cbeba', 26350418, 'C-1 of capture 26350419 (repaid 2.118)'),
 ('0xebf1ad18c0d4d1b3fe227f511f746a319a5cbeba', 26342362, 'C-1 of capture 26342363 (repaid 0.302)'),
 ('0x741bf6d2ccb8802c831f1cc12a30105e3f6e0755', 26350419, 'C-1 of capture 26350420 (repaid 0.65)'),
]
for b,tag,desc in tests:
    l,h=probe(b,tag)
    print(desc, '|', tag, '| isLiquidatable=',l,'| isHealthy=',h)
