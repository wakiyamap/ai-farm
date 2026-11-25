import json, urllib.request, os
url = os.environ['RPC_RELAY_URL'] + '/ethereum?lane=research'
def rpc(method, params):
    body = json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    req = urllib.request.Request(url, body, headers={"content-type":"application/json"})
    r = json.loads(urllib.request.urlopen(req).read())
    if "error" in r: print("ERR", r["error"]); 
    return r["result"]
logs = rpc("eth_getLogs", [{"address":["0x3e6eba46abc5ab18ed95f6667d8b2fd4020e4637"],"fromBlock":"0x1922415","toBlock":"0x1922421"}])
print("n", len(logs))
for l in logs:
    print(l["transactionHash"], l["topics"][0][:66], len(l["topics"]))
open("scratch/pendle-log-topics.json","w").write(json.dumps(logs))
