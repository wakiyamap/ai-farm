import json, os, urllib.request
U = os.environ["RPC_RELAY_URL"]
CETH = "0x4ddc2d193948926d02f9b1fe9e1daa0718270ed5"
def rpc(method, params):
    body = json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    req = urllib.request.Request(U+"/ethereum?lane=research", data=body, headers={"content-type":"application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=90).read())
def accrue(mant, tag, frm="0x8f10b468b06c6fd214b65f87778827f7d113f996"):
    data = "0xdb006a75" + "%064x" % mant
    r = rpc("eth_call", [{"to":CETH,"from":frm,"data":data}, tag])
    if "error" in r: return "REVERT " + r["error"].get("message","")[:60]
    return "OK ret=" + r["result"][-12:]
tests = [
 ("mant=1e8 @head", accrue(10**8, "latest")),
 ("mant=8322739013 @head", accrue(8322739013, "latest")),
 ("mant=8301660664 @head (bot param)", accrue(8301660664, "latest")),
 ("mant=8322739013 @26365771", accrue(8322739013, hex(26365771))),
 ("mant=45117721 @26365771", accrue(45117721, hex(26365771))),
 ("mant=1e18 @head", accrue(10**18, "latest")),
 ("mant=2e9 @head", accrue(2*10**9, "latest")),
]
for k,v in tests: print(k, "->", v)
