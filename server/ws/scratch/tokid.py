import json, urllib.request, os, sys
RL = os.environ['RPC_RELAY_URL'] + '/ethereum?lane=research'
def call(to, data):
    req = json.dumps({"jsonrpc":"2.0","id":1,"method":"eth_call","params":[{"to":to,"data":data},"latest"]}).encode()
    r = json.loads(urllib.request.urlopen(urllib.request.Request(RL, req, headers={'content-type':'application/json'}), timeout=30).read())
    return r.get('result') or r.get('error')
def sym(d):
    if not isinstance(d,str) or len(d)<10: return d
    h=d[2:]
    off=int(h[:64],16)*2
    ln=int(h[off:off+64],16)*2
    return bytes.fromhex(h[off+64:off+64+ln]).decode('utf-8','replace') if off+64+ln<=len(h) else None
toks = {
 '0x27f2f159fe990ba83d57f39fd69661764bebf37a':'sell',
 '0x7133ebcb1a23e3d8be7ff09362b02b2a2e4c3da4':'sell',
 '0x7f39c581f595b53c5cb19bd0b3f8da6c935e2ca0':'sell',
 '0x8c106eedad96553e64287a5a6839c3cc78afa3d0':'sell',
 '0x9a1d6bd5b8642c41f25e0958129b85f8e1176f3e':'sell',
 '0xa0d69e286b938e21cbf7e51d71f6a4c8918f482f':'both',
 '0xac3e018457b222d93114458476f3e3416abbe38f':'sell',
 '0xb576765fb15505433af24fee2c0325895c559fb2':'sell',
 '0xcd5fe23c85820f7b72d0926fc9b05b43e359b7ee':'sell',
 '0xe72b141df173b999ae7c1adcbf60cc9833ce56a8':'both',
 '0x320623b8e4ff03373931769a31fc52a4e78b5d70':'buy',
}
for t,role in toks.items():
    s = call(t,'0x06fdde03'); d = call(t,'0x95d09600')
    print(t, role, sym(s) if isinstance(s,str) else s, d if isinstance(d,str) else d, flush=True)
