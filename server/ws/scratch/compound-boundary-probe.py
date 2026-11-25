import json, os, urllib.request
U = os.environ["RPC_RELAY_URL"]
CETH = "0x4ddc2d193948926d02f9b1fe9e1daa0718270ed5"
def rpc(method, params):
    body = json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    req = urllib.request.Request(U+"/ethereum?lane=research", data=body, headers={"content-type":"application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=90).read())
def accrue(mant, frm="0x8f10b468b06c6fd214b65f87778827f7d113f996"):
    data = "0xdb006a75" + "%064x" % mant
    r = rpc("eth_call", [{"to":CETH,"from":frm,"data":data}, "latest"])
    if "error" in r: return "REVERT " + r["error"].get("message","")[:40]
    return "OK ret=" + r["result"][-8:]
# head state reads for the derived supply candidate
for name, sig, extra in [("borrowRatePerBlock","0x0000000000000000000000000000000000000000000000000000000000000000",None)]: pass
br = int(rpc("eth_call",[{"to":CETH,"data":"0x"+ "ae9d70b0"},"latest"])["result"],16) if True else None
