import json, urllib.request
RELAY="http://127.0.0.1:8545"
def rpc(method, params):
    body=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    req=urllib.request.Request(RELAY+"/ethereum?lane=research", data=body, headers={"content-type":"application/json"})
    r=json.loads(urllib.request.urlopen(req, timeout=90).read())
    if "error" in r: print("ERR", method, json.dumps(r["error"])); return None
    return r["result"]
bn=rpc("eth_blockNumber",[])
n=int(bn,16); print("head:", n, hex(n))
tag=hex(n-200)
for a in ["0x3d9819210a31b4961b30ef54be2aed79b9c9cd3b","0x4ddc2d193aaf8ce8c9ceb5ed6bd6ee6ef4190e6e"]:
    code=rpc("eth_getCode",[a,tag])
    print(a, "code len:", len(code)-2 if code else code)
