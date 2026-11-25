import json, urllib.request, os
URL = os.environ["RPC_RELAY_URL"] + "/ethereum?lane=research"
def rpc(method, params):
    body = json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    req = urllib.request.Request(URL, body, headers={"content-type":"application/json"})
    r = json.loads(urllib.request.urlopen(req, timeout=60).read())
    if "error" in r: raise RuntimeError(json.dumps(r["error"])[:200])
    return r["result"]
VAULT = "0x1344a36a1b56144c3bc62e7757377d288fde0369"
for a,b in [(20800000,20860000),(21500000,21560000),(23000000,23060000),(24200000,24260000)]:
    logs = rpc("eth_getLogs", [{"address": VAULT, "fromBlock": hex(a), "toBlock": hex(b)}])
    print(a,b,len(logs))
