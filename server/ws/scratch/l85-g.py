import json, urllib.request, sys
RELAY="http://127.0.0.1:8545"
CETH="0xe65cdb6479bac1e22340e4e755fae7e509ecd06c"
REC="0x8f10b468b06c6fd214b65f87778827f7d113f996"
def rpc(method, params):
    body=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    req=urllib.request.Request(RELAY+"/ethereum?lane=research", data=body, headers={"content-type":"application/json"})
    r=json.loads(urllib.request.urlopen(req, timeout=90).read())
    if "error" in r: print("ERR", method, json.dumps(r["error"])); return "ERR"
    return r["result"]
r=rpc("eth_call",[{"to":CETH,"data":"0x70a08231"+REC[2:]},"latest"])
print("balanceOf @latest:", int(r,16)/1e8 if r!="ERR" and r not in (None,"0x") else r)
r=rpc("eth_call",[{"to":CETH,"data":"0x70a08231"+REC[2:]},"0x1917885"])  # 26365189
print("balanceOf @26365189:", int(r,16)/1e8 if r!="ERR" and r not in (None,"0x") else r)
r=rpc("eth_call",[{"to":CETH,"data":"0x70a08231"+REC[2:]},"0x1917886"])  # 26365190
print("balanceOf @26365190:", int(r,16)/1e8 if r!="ERR" and r not in (None,"0x") else r)
