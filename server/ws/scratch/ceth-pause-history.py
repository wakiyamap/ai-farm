import json, urllib.request
RELAY = "http://127.0.0.1:8545"
CETH = "0x4ddc2d193948926d02f9b1fe9e1daa0718270ed5"
def call(data, tag, to=CETH):
    body = json.dumps({"jsonrpc":"2.0","id":1,"method":"eth_call","params":[{"to":to,"data":data},tag]})
    req = urllib.request.Request(f"{RELAY}/ethereum?lane=research", data=body.encode(), headers={"content-type":"application/json"})
    try:
        r = json.load(urllib.request.urlopen(req, timeout=40))
    except Exception as e:
        return ("EXC", str(e))
    if "error" in r: return ("ERR", str(r["error"])[:70])
    return ("OK", r["result"])
BORROWRATE = "0xc914b437"
ACCRUAL = "0x6c540baf"
blocks = [26340000, 26348000, 26354000, 26360000, 26364052, 26364053, 26365771, 26366500, 26367800, 26368500]
for n in blocks:
    tag = hex(n)
    st, res = call(BORROWRATE, tag)
    st2, res2 = call(ACCRUAL, tag)
    extra = ""
    if st2 == "OK":
        extra = f" accrualBlock={int(res2,16)}"
    print(f"block {n}: borrowRate {st} {res if st=='ERR' else int(res,16)}{extra}")
