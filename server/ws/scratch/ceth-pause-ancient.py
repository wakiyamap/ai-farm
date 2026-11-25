import json, urllib.request
RELAY = "http://127.0.0.1:8545"
CETH = "0x4ddc2d193948926d02f9b1fe9e1daa0718270ed5"
def call(data, tag, to=CETH):
    body = json.dumps({"jsonrpc":"2.0","id":1,"method":"eth_call","params":[{"to":to,"data":data},tag]})
    req = urllib.request.Request(f"{RELAY}/ethereum?lane=research", data=body.encode(), headers={"content-type":"application/json"})
    try:
        r = json.load(urllib.request.urlopen(req, timeout=45))
    except Exception as e:
        return ("EXC", str(e)[:60])
    if "error" in r: return ("ERR", (str(r["error"].get("message") if isinstance(r["error"],dict) else r["error"]))[:40])
    return ("OK", r["result"])
BORROWRATE = "0xc914b437"
MINT96 = "0x5f7c7af1"
for n in [14000000, 15000000, 16000000, 18000000]:
    st, res = call(BORROWRATE, hex(n))
    st2, res2 = call(MINT96 + hex(10**15)[2:].rjust(64,"0"), hex(n)) if True else None
    print(f"block {n}: borrowRate {st} {res}; mint(uint96) {st2} {res2}")
