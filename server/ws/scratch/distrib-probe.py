import json, urllib.request, time
RPC="http://127.0.0.1:8545"
def rpc(method, params, lane="research"):
    body=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    req=urllib.request.Request(f"{RPC}/ethereum?lane={lane}", body, headers={"content-type":"application/json"})
    for i in range(4):
        try:
            return json.loads(urllib.request.urlopen(req, timeout=60).read())["result"]
        except Exception:
            time.sleep(2)
topic0="0xddc9c30275a04c48091f24199f9c405765de34d979d6847f5b9798a57232d2e5"
addr=["0x3d9819210A31B4DE2A5E6c37681e6624EEFC8af6"]
for lo in [12000000,13000000,14000000,15000000,16000000,17000000,18000000]:
    logs=rpc("eth_getLogs",[{"fromBlock":hex(lo),"toBlock":hex(lo+9999),"address":addr,"topics":[topic0]}])
    print(lo, len(logs), [hex(int(l['blockNumber'],16)) for l in logs][:5])
