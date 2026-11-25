import json, os, sys, urllib.request
URL=os.environ["RPC_RELAY_URL"]
def rpc(chain, method, params, lane="research"):
    body=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    req=urllib.request.Request(f"{URL}/{chain}?lane={lane}", data=body, headers={"content-type":"application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        d=json.loads(r.read().decode())
    if "error" in d: raise RuntimeError(d["error"])
    return d["result"]
