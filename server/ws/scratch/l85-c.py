import json, urllib.request
RELAY="http://127.0.0.1:8545"
COMP="0x3d9819210a31b4961b30ef54be2aed79b9c9cd3b"
def rpc(method, params):
    body=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    req=urllib.request.Request(RELAY+"/ethereum?lane=research", data=body, headers={"content-type":"application/json"})
    r=json.loads(urllib.request.urlopen(req, timeout=90).read())
    if "error" in r: print("ERR", method, json.dumps(r["error"])); return None
    return r["result"]
res=rpc("eth_call",[{"to":COMP,"data":"0x9abd03ee"},"latest"])  # getAllMarkets()
if res:
    addrs=[res[i:i+64][24:64] for i in range(0,len(res),128)//1]
    # proper decode: 32-byte words after offset
    off=int(res[2:66],16)
    n=(len(res)-2-64)//128  # placeholder
    words=[res[64+2*i:64+64+2*i] for i in range((len(res)-66)//128)]
    markets=[ "0x"+w[24:] for w in words[1:]] if False else ["0x"+w[24:] for w in words[1:]]
    print(len(markets),"markets")
    for m in markets:
        print(m)
