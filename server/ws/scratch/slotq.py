import json, urllib.request
URL="http://127.0.0.1:9003"
def rpc(m,p):
    b=json.dumps({"jsonrpc":"2.0","id":1,"method":m,"params":p}).encode()
    r=urllib.request.Request(URL,data=b,headers={"content-type":"application/json"})
    o=json.loads(urllib.request.urlopen(r,timeout=60).read())
    return o.get("result") or o.get("error")
IMPL_SLOT="0x360894a13ba7a36aeae9452645d58f48819aacfc79de3ff8c2b5b80edd0fc202"
for a in ["0xbfebc5ecac789643a61fadf15048a37dc9612dcf","0xa88cd6b934c64ea830b78967b2f8a0de91577edc"]:
    v=rpc("eth_getStorageAt",[a,IMPL_SLOT,"latest"])
    print(a[:10], "->impl", v)
