import json, urllib.request, os
URL = os.environ["RPC_RELAY_URL"]; LANE="research"
def rpc(method, params):
    req = urllib.request.Request(f"{URL}/hyperevm?lane={LANE}",
        data=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode(),
        headers={"content-type":"application/json"})
    r = json.loads(urllib.request.urlopen(req, timeout=30).read())
    if "error" in r: return None
    return r["result"]
head = int(rpc("eth_blockNumber",[]),16)
def try_str(r):
    if not r or len(r)<=4: return None
    hexs=r[2:]
    body=bytes.fromhex(hexs[64:] if len(hexs)>=136 else hexs)
    s=body.rstrip(b"\x00").decode("utf-8","replace").split("\x00")[0]
    return s[:40] or None
for a in ["0x90dabc988d2ae90c10e551f82129dc0bb0e11d29","0x233ff29b239abc1d7748605da9b205c3e008626e","0x278d858f05b94576c1e6f73285886876ff6ef8d2"]:
    for fname,sel in [("name","0x06fdde03"),("symbol","0x95d8cba9")]:
        s=try_str(rpc("eth_call",[{"to":a,"data":sel},"latest"]))
        print(a[:12], fname, repr(s))
tr = rpc("alchemy_getAssetTransfers",[{"fromBlock":hex(head-300000),"toBlock":hex(head-100),"category":["external"],"maxCount":"0x64","toAddress":"0x33b12dd75f66933acd6438594d80cf91cacdc10b"}])
print("0x33b12dd7 7d native in:", len(tr["transfers"]) if tr else "ERR", [ (t["from"][:10], t.get("rawValue")) for t in (tr["transfers"][:6] if tr else [])])
