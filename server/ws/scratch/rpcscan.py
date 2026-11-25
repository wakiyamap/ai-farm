import json, urllib.request, os
URL=os.environ['RPC_RELAY_URL']
def rpc(chain, method, params, lane="research"):
    req=urllib.request.Request(f"{URL}/{chain}?lane={lane}", data=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode(), headers={"content-type":"application/json"}, method="POST")
    return json.loads(urllib.request.urlopen(req, timeout=60).read())
