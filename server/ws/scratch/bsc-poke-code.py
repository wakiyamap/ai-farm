import json, urllib.request, os
RELAY = os.environ["RPC_RELAY_URL"]
def rpc(method, params, chain="bsc", lane="research"):
    body = json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    req = urllib.request.Request(f"{RELAY}/{chain}?lane={lane}", data=body,
        headers={"content-type":"application/json"})
    r = json.loads(urllib.request.urlopen(req, timeout=90).read())
    if "error" in r: print("ERR", r["error"]); return None
    return r["result"]
for a in ["0x8b0dcb783b09890f9ecef4f93d782f55f549578e","0x1ca6d29763a9b6b49bbde2f0b102d03b9b6a8f54","0x293f3a7d33ceb26d3a33426dcac325596a8539c7"]:
    code = rpc("eth_getCode", [a, "latest"])
    print(a, "code_len_bytes", max(0,len(code)//2-2))
    # try ERC20-ish getters
    for sig,fn in [("0x06fdde03","name()"),("0x95d8c48c","symbol()"),("0x70a08231","balanceOf(u)"),("0x481c6a75","totalClaimed?")]:
        r = rpc("eth_call", [{"to":a,"data":sig}, "latest"])
        if r and r != "0x":
            if fn=="balanceOf(u)": r = r.replace("0x"+"0"*24, "0x")
            print("  ", fn, r[:80])
