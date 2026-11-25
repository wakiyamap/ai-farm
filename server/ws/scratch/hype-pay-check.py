import json, urllib.request, os
URL = os.environ["RPC_RELAY_URL"]; LANE="research"
def rpc(method, params):
    req = urllib.request.Request(f"{URL}/hyperevm?lane={LANE}",
        data=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode(),
        headers={"content-type":"application/json"})
    r = json.loads(urllib.request.urlopen(req, timeout=40).read())
    if "error" in r: print("ERR", method, str(r["error"])[:120]); return None
    return r["result"]
head = int(rpc("eth_blockNumber",[]),16)
cands = {
 "0x6d18f44e6b64e5e44bbaca1ca534a8290bd331b5": "0x2745cbaa0aafc99b5285e5ade53fdf79c2a488f5",
 "0xdf1bda875c9393a663ce69bf6a7fbaa73dfd053d": "0x6cd5661646289fb6e65ea5c032310fded797d0a2",
 "0x33b12dd75f66933acd6438594d80cf91cacdc10b": "0xf9b0c8ee13ae2fc0665764ecbdb417685dea8081",
 "0xaea0edc9ae3939f89e11d19d09d96a32ccefb5e2": "0xce59f8b65ad41c9dae4c07a0571a39824bd92cff",
}
for caller, target in cands.items():
    tr = rpc("alchemy_getAssetTransfers",[{"fromBlock":hex(head-300000),"toBlock":hex(head-100),
         "category":["erc20"],"maxCount":"0x64","toAddress":caller}])
    if tr is not None:
        import collections
        c=collections.Counter((t["asset"], t["from"]) for t in tr["transfers"])
        tot={}
        for t in tr["transfers"]:
            v=float(t.get("rawAmount") or 0)/ (10**t.get("token",{}).get("decimals",18) if t.get("token") else 1e6)
            tot[t["asset"]]=tot.get(t["asset"],0)+v
        print(f"{caller[:10]} 7d erc20 in: {len(tr['transfers'])} transfers", dict(c.most_common(6)), {k:round(v,4) for k,v in tot.items()})
# name/symbol on poked contracts
for target in set(cands.values()):
    for fname, sel in [("name","0x06fdde03"),("symbol","0x95d8cba9"),("owner","0x8da5cb5b")]:
        r = rpc("eth_call",[{"to":target,"data":sel},"latest"])
        if r and len(r)>2:
            raw=bytes.fromhex(r[2:]).decode("utf-8","replace") if len(r)>10 else r
            dec = raw.split("\x00")[0][:40] if len(r)>10 else r[:10]
            print(f"{target[:10]} {fname}(): {dec!r}" if dec else "")
            break
