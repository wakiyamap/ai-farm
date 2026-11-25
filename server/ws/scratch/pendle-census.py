import json, urllib.request, os
url = os.environ['RPC_RELAY_URL'] + '/ethereum?lane=research'
def rpc(method, params):
    body = json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    req = urllib.request.Request(url, body, headers={"content-type":"application/json"})
    return json.loads(urllib.request.urlopen(req).read())["result"]
head = int(rpc("eth_blockNumber", []), 16)
t0 = "0xaa79d8f17776adeaa316c5411b72e8b0057d064974fa8748f32492ecaa22ecd1"
addrs = ["0x3e6eba46abc5ab18ed95f6667d8b2fd4020e4637","0x273b4bfa3bb30fe8f32c467b5f0046834557f072","0x35a338522a435d46f77be32c70e215b813d0e3ac"]
logs = rpc("eth_getLogs", [{"address":addrs,"topics":[t0],"fromBlock":hex(head-2160000),"toBlock":hex(head)}])
bn = sorted(int(l["blockNumber"],16) for l in logs)
print("head",head,"n",len(logs))
print("first",bn[0] if bn else None,"last",bn[-1] if bn else None)
gaps = [bn[i+1]-bn[i] for i in range(len(bn)-1)]
big = sorted(g for g in gaps if g>100)
print("batch gaps >100 blocks:", big[:10])
print("expiries:", sorted(set(int(l["topics"][2],16) for l in logs)))
open("scratch/pendle-census.json","w").write(json.dumps(logs))
