import json, urllib.request, sys
RELAY="http://127.0.0.1:8545"
CETH="0x4ddc2d193aaf8ce8c9ceb5ed6bd6ee6ef4190e6e"
def rpc(method, params):
    body=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    req=urllib.request.Request(RELAY+"/ethereum?lane=research", data=body, headers={"content-type":"application/json"})
    r=json.loads(urllib.request.urlopen(req, timeout=90).read())
    if "error" in r: print("ERR", method, json.dumps(r["error"])); return None
    return r["result"]
code=rpc("eth_getCode",[CETH,"latest"])
print("code len:", len(code) if code else code, "head:", (code[:40] if code else None))
r=rpc("eth_call",[{"to":CETH,"data":"0x70a08231"+"3d9819210a31b4961b30ef54be2aed79b9c9cd3b"},"latest"])
print("balanceOf(comptroller):", r)
