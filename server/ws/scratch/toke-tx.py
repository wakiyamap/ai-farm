import json, urllib.request, time
RPC="http://127.0.0.1:8545"
def rpc(method, params, chain="ethereum", lane="research"):
    body=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    req=urllib.request.Request(f"{RPC}/{chain}?lane={lane}", body, headers={"content-type":"application/json"})
    for i in range(4):
        try:
            return json.loads(urllib.request.urlopen(req, timeout=60).read())["result"]
        except Exception:
            time.sleep(2)
for h in ["0xf2e00057c34306e5aef11462a387f5606524a3775cf7fcdee47d1c28420aceea","0x1a06d8c57febcedf49a365014d95bec288c9dd66879bc029abf793b0f4a809bc"]:
    t=rpc("eth_getTransactionByHash",[h])
    print("tx", h[:14], "from", t["from"], "to", t["to"], "gasUsed", t.get("gasUsed"), "input", t["input"][:10])
