import json, os, urllib.request
RELAY = os.environ["RPC_RELAY_URL"]
HUB = "0xDE12B620A8a714476A97EfD14E6F7180Ca653557"
def rpc(method, params, lane="research"):
    body = json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    req = urllib.request.Request("%s/ethereum?lane=%s" % (RELAY, lane), data=body, headers={"content-type":"application/json"})
    d = json.loads(urllib.request.urlopen(req, timeout=90).read())
    if "error" in d: raise SystemExit("ERR %s: %s" % (method, d["error"]))
    return d["result"]
head = int(rpc("eth_blockNumber",[]),16)
logs = rpc("eth_getLogs",[{"address":HUB,"fromBlock":26403144,"toBlock":head}])
for e in logs:
    ts = int(rpc("eth_getBlockByNumber",[e["blockNumber"],False])["timestamp"],16)
    print("block", int(e["blockNumber"],16), "ts", ts, "topic0", e["topics"][0][2:10], "tx", e["transactionHash"])
    print("  topics:", [t[2:] for t in e["topics"]][1:])
    print("  data:", e["data"])
