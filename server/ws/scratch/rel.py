import json, os, sys, urllib.request
def rel(chain, method, params, lane="research"):
    url=f"{os.environ['RPC_RELAY_URL']}/{chain}?lane={lane}"
    body=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    req=urllib.request.Request(url, data=body, headers={"content-type":"application/json"})
    with urllib.request.urlopen(req, timeout=60) as r: return json.loads(r.read().decode())
