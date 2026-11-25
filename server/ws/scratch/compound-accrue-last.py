import json, os, urllib.request
U = os.environ["RPC_RELAY_URL"]
def rpc(method, params, lane="research"):
    body = json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    req = urllib.request.Request(U+"/ethereum?lane="+lane, data=body, headers={"content-type":"application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=90).read())
CETH = "0x4ddc2d193948926d02f9b1fe9e1daa718270ed5"  # will fix below
CETH = "0x4ddc2d193948926d02f9b1fe9e1daa0718270ed5"
t1 = "0x"+"%064x" % int(CETH, 16)
r = rpc("eth_getLogs", [{"fromBlock":"0x"+"%x" % 26370200, "toBlock":"0x"+"%x" % 26370300, "address":["0x3d9819210a31b4961b30ef54be2aed79b9c9cd3b"],"topics":[None, t1]}])
if "error" in r: print("ERR", r["error"]); raise SystemExit
for log in r["result"]:
    print(log["blockNumber"], log["transactionHash"], log["topics"][0][:20], "w0=", log["data"][66:130], len(log["data"]))
