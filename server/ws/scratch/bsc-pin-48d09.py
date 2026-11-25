import json, os, time, urllib.request

URL = os.environ["RPC_RELAY_URL"] + "/bsc?lane=research"
def rpc(method, params=None):
    body = json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params or []}).encode()
    req = urllib.request.Request(URL, data=body, headers={"content-type":"application/json"})
    for i in range(2):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                d = json.loads(r.read())
            if "error" in d:
                return None
            return d["result"]
        except Exception:
            time.sleep(2)
    return None

SEL={"name()":"0x06fdde03","symbol()":"0x95d8823e","getReserves()":"0x0908f566","factory()":"0xc45a9855","WBNB()":"0x8b243dad","totalSupply()":"0x06fdde03","pairImplementation()":"0xd6d4fc21","deposit()":"0xd0e30139"}
addrs=["0x7a1625e3081dc503e86f3982e0422ca3dd9818a1","0xad1e8dbeb37ca30fa06964e1ac127ad9c132ae7b",
"0xd47fe2423f61becaf283ed78a8afec587b8530c5","0x568ee9a7c25eae5bb1b881e5d81f14640dc7066a",
"0x8bc070bedab741406f4b1eb65a72bee27894b689","0xa5dbeaf16fc031eae92175974f8d0a439be4ad17",
"0x238a358808379702088667322f80ac48bad5e6c4","0x9999b0cdd35d7f3b281ba02efc0d228486940515",
"0x28e2ea090877bf75740558f6bfb36a5ffee9e9df","0x22da1810b194ca018378464a58f6ac2b10c9d244"]
res={}
for a in addrs:
    code=rpc("eth_getCode",[a,"latest"])
    clen=(len(code)-2)//2 if code else -1
    hits=[]
    if clen>0:
        for fn,sel in SEL.items():
            if sel[2:].lower() in code.lower():
                hits.append(fn)
    res[a]={"code_len":clen,"selectors":hits[:8]}
    print(a,res[a],flush=True)
json.dump(res, open("scratch/bsc-pin-48d09.json","w"))
