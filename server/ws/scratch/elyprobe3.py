import json, urllib.request, os
URL=os.environ['RPC_RELAY_URL']; LANE='research'
def rpc(m,p=None):
    b=json.dumps({"jsonrpc":"2.0","id":1,"method":m,"params":p or []}).encode()
    req=urllib.request.Request(f"{URL}/elysium?lane={LANE}",b,{"content-type":"application/json"})
    r=json.loads(urllib.request.urlopen(req,timeout=60).read())
    if 'error' in r: return ('ERR', json.dumps(r['error'])[:60])
    return ('OK', r['result'])
cands=["0x0729e2a4716d9f7dd17858d5d504426d228697f7","0x195627f03fe2668d65c763cd39eec45b1d76c8ee",
"0xb2766443c2f92fbe579f057593802737bc88f591","0x8f10b468b06c6fd214b65f87778827f7d113f996",
"0x4cd00e387622c35bddb9b4c962c136462338bc31","0x939e398d2c31b0757d009222de99c6e461d3de15",
"0x8b3bcaf34559f781421277626ebb51fb09ce360f","0x5567954cd026cebfe486062cb75848e0f1c12e58",
"0x047b4355b8497b6588d38f39057d129478bdd3e8","0x1707327F626496A7b5b3872e7E4d2879Df7d7a9f",
"0xEfd7A089D3057F05189B05f74Ffcf30610c42891","0xBbBcC62853a5fA27b93d6Bab3E6F7ce841E25Df2"]
S={'token0()':'0x0dfe1681','balance()':'0xb69ef8a8','getReserves()':'0x0902f1ac'}
for a in cands:
    out=[]
    for n,d in S.items():
        st,r=rpc("eth_call",[{"to":a,"data":d},"latest"])
        out.append(f"{n}:{'OK '+str(r)[:18] if st=='OK' else 'rv'}")
    print(a[:12], " | ".join(out))
