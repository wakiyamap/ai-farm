import json, urllib.request
RELAY = "http://127.0.0.1:8545"
OLD = "0x06febf36yry2u2df62p31cyb3dde6d536f6054fc"
def call(to, data, value=None):
    p = {"to":to,"data":data}
    if value: p["value"]=value
    body = json.dumps({"jsonrpc":"2.0","id":1,"method":"eth_call","params":[p,"latest"]})
    req = urllib.request.Request(f"{RELAY}/ethereum?lane=research", data=body.encode(), headers={"content-type":"application/json"})
    r = json.load(urllib.request.urlopen(req, timeout=40))
    if "error" in r: return ("ERR", str(r["error"].get("message") if isinstance(r["error"],dict) else r["error"]))
    return ("OK", r["result"])
MINT256 = "0xa0712d68" + hex(10**17)[2:].rjust(64,"0")
st,res = call(OLD, MINT256, hex(10**17))
print("old cETH mint(uint256) 0.1 ETH:", st, res[:50])
st,res = call(OLD, "0xa0712d68" + "0"*64, "0x0")
print("old cETH mint(0) no value:", st, res[:50])
st,res = call(OLD, "0x182df0f5")
print("old cETH exchangeRateStored:", st, res[:60])
st,res = call(OLD, "0x18160ddd")
print("old cETH totalSupply:", st, res[:60])
