import json, urllib.request, os, sys
URL=os.environ['RPC_RELAY_URL']; LANE='research'
def rpc(m,p=None):
    b=json.dumps({"jsonrpc":"2.0","id":1,"method":m,"params":p or []}).encode()
    req=urllib.request.Request(f"{URL}/elysium?lane={LANE}",b,{"content-type":"application/json"})
    r=json.loads(urllib.request.urlopen(req,timeout=90).read())
    if 'error' in r: print(m, r['error']); return None
    return r["result"]
for a,pats in [("0x4cd00e387622c35bddb9b4c962c136462338bc31",["2d9fb478","0a2b8f36"]),
               ("0x5567954cd026cebfe486062cb75848e0f1c12e58",["0a2b8f36","f4993018"]),
               ("0x047b4355b8497b6588d38f39057d129478bdd3e8",["f4993018","2d9fb478"])]:
    c=rpc("eth_getCode",[a,"latest"])
    if c is None: continue
    body=c[2:] if c.startswith("0x") else c
    print(a[:10], "code bytes:", len(body)//2, {p: (p in body) for p in pats})
