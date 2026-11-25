import json, urllib.request, sys
RELAY="http://127.0.0.1:8545"
M="0xe65cdb6479bac1e22340e4e755fae7e509ecd06c"
def rpc(method, params):
    body=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    req=urllib.request.Request(RELAY+"/ethereum?lane=research", data=body, headers={"content-type":"application/json"})
    r=json.loads(urllib.request.urlopen(req, timeout=90).read())
    if "error" in r: print("ERR", method, json.dumps(r["error"])[:120]); return "ERR"
    return r["result"]
def dec_str(x):
    if x=="ERR" or not x or len(x)<130: return x[:60]
    off=int(x[2:66],16)*2; ln=int(x[off:off+64],16)*2
    return bytes.fromhex(x[off+64:off+64+ln]).decode()
print("symbol:", dec_str(rpc("eth_call",[{"to":M,"data":"0x95d89b02"},"latest"])))
print("name:", dec_str(rpc("eth_call",[{"to":M,"data":"0x06fdde03"},"latest"])))
print("underlying:", dec_str(rpc("eth_call",[{"to":M,"data":"0x404e800d"},"latest"])))  # UnderlyingInterestRate? no; try underlying() 0x
