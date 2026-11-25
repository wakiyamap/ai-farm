import json, urllib.request, os
URL=os.environ['RPC_RELAY_URL']; LANE='research'
def rpc(m,p=None):
    b=json.dumps({"jsonrpc":"2.0","id":1,"method":m,"params":p or []}).encode()
    req=urllib.request.Request(f"{URL}/elysium?lane={LANE}",b,{"content-type":"application/json"})
    r=json.loads(urllib.request.urlopen(req,timeout=60).read())
    if 'error' in r: return ('ERR', json.dumps(r['error'])[:140])
    return ('OK', r['result'])
USDC="0xb47c4C8F73F009CC0C0d3f92B388d13E293F0B65"
addr=["0x0729e2a4716d9f7dd17858d5d504426d228697f7","0x195627f03fe2668d65c763cd39eec45b1d76c8ee",
"0xb2766443c2f92fbe579f057593802737bc88f591","0x8f10b468b06c6fd214b65f87778827f7d113f996",
"0x4cd00e387622c35bddb9b4c962c136462338bc31","0x939e398d2c31b0757d009222de99c6e461d3de15",
"0x8b3bcaf34559f781421277626ebb51fb09ce360f","0x97796d80b6a1db78632f7451196b04f307329eb6",
"0x5567954cd026cebfe486062cb75848e0f1c12e58","0x047b4355b8497b6588d38f39057d129478bdd3e8"]
SEL={'slot0()':'0x3850c7bd','token()':'0xfc0c546a','flashFee':'0xd9d98ce4'+USDC[2:]+ '00000000000000000000000000000000000000000000000000000000000f4240'}
for a in addr:
    st,res=rpc("eth_call",[{"to":a,"data":SEL['slot0()']},"latest"])
    print(a[:12], "slot0:", (res[:20] if st=='OK' else res))
