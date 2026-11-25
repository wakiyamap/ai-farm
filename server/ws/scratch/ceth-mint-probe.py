import json, urllib.request
RELAY = "http://127.0.0.1:8545"
CETH = "0x4ddc2d193948926d02f9b1fe9e1daa0718270ed5"
def call(frm, data, value, tag="latest", to=CETH):
    p = {"to":to,"data":data}
    if frm: p["from"]=frm
    if value: p["value"]=value
    body = json.dumps({"jsonrpc":"2.0","id":1,"method":"eth_call","params":[p,tag]})
    req = urllib.request.Request(f"{RELAY}/ethereum?lane=research", data=body.encode(), headers={"content-type":"application/json"})
    r = json.load(urllib.request.urlopen(req, timeout=40))
    if "error" in r: return ("ERR", str(r["error"].get("message") if isinstance(r["error"],dict) else r["error"]))
    return ("OK", r["result"])
arg = hex(10**17)[2:]  # 0.1 ETH
pad = arg.rjust(64,"0")
MINT96 = "0x5f7c7af1"
MINT256 = "0xa0712d68"
MINT_A96 = "0x1b025a40"
EOA = "0x1111111111111111111111111111111111111111"
for name, sel in [("mint(uint96)",MINT96),("mint(uint256)",MINT256),("mint(address,uint96)",MINT_A96)]:
    if sel == MINT_A96:
        data = sel + EOA[2:].lower().rjust(64,"0") + pad
    else:
        data = sel + pad
    st, res = call(EOA, data, hex(10**17))
    print(name, "->", st, res[:60])
# also redeemUnderlying(0.001e18) from zero balance
RED = "0x852a12e3"
st, res = call(EOA, RED + hex(10**15)[2:].rjust(64,"0"), "0x0")
print("redeemUnderlying(1e15) zero-pos ->", st, res[:60])
