import json, urllib.request, os, sys
URL=os.environ['RPC_RELAY_URL']; LANE='research'
def call(to,data):
    p={"jsonrpc":"2.0","id":1,"method":"eth_call","params":[{"to":to,"data":data},"latest"]}
    rq=urllib.request.Request(f"{URL}/base?lane={LANE}",data=json.dumps(p).encode(),headers={"content-type":"application/json"})
    r=json.loads(urllib.request.urlopen(rq,timeout=60).read())
    return r.get('result') or ('ERR '+r['error'].get('message',''))
for m in ["0xde8df9d942d78ede3ca06e60712582f79cfffc64","0x3bf93770f2d4a794c3d9ebefbaebae2a8f09a5e5","0xdc7810b47eaab250de623f0ee07764afa5f71ed1","0x703843c3379b52f9ff486c9f5892218d2a065cc8","0xb682c840b5f4fc58b20769e691a6fa1305a501a2"]:
    print(m, 'underlying=', call(m,"0x6d342007"), 'name=', call(m,"0x06fdde03"))
