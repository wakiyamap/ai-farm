import json, urllib.request, subprocess, time
RPC="http://127.0.0.1:8545"
def rpc(method, params, chain="ethereum", lane="research"):
    body=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    req=urllib.request.Request(f"{RPC}/{chain}?lane={lane}", body, headers={"content-type":"application/json"})
    for i in range(4):
        try:
            r=json.loads(urllib.request.urlopen(req, timeout=60).read())
            return r.get("result", r.get("error"))
        except Exception as e:
            time.sleep(2)
out=subprocess.check_output(["cast","keccak","distHash()"], text=True)
sel="0x"+out.strip()[2:10]
print("selector", sel)
res=rpc("eth_call",[{"to":"0x3d9819210A31B4DE2A5E6c37681e6624EEFC8af6","data":sel},"latest"])
print("distHash() ->", res)
# also check the Comptroller emits ANY events recently (proxy identity check): all logs on address, 14d
head=int(rpc("eth_blockNumber",[]),16)
logs=rpc("eth_getLogs",[{"fromBlock":hex(head-49000),"toBlock":hex(head),"address":["0x3d9819210A31B4DE2A5E6c37681e6624EEFC8af6"]}])
print("all-event logs last 7d on comptroller:", len(logs), [ (l['topics'][0][:14], hex(int(l['blockNumber'],16))) for l in logs[:4]])
