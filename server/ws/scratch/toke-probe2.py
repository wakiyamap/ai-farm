import json, urllib.request, subprocess, time
RPC="http://127.0.0.1:8545"
def rpc(method, params, chain="ethereum", lane="research"):
    body=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    req=urllib.request.Request(f"{RPC}/{chain}?lane={lane}", body, headers={"content-type":"application/json"})
    for i in range(4):
        try:
            return json.loads(urllib.request.urlopen(req, timeout=60).read())["result"]
        except Exception:
            time.sleep(2)
mgr="0xA86e412109f77c45a3BC1c5870b880492Fb86A14"
t0="0x"+subprocess.check_output(["cast","keccak","CycleRolloverStarted(uint256)"],text=True).strip()[2:][:64]
for lo in [12000000,13000000,15000000,17000000,19000000]:
    r=rpc("eth_getLogs",[{"fromBlock":hex(lo),"toBlock":hex(lo+9999),"address":[mgr],"topics":[t0]}])
    print(lo, len(r), [(hex(int(l['blockNumber'],16)),l['transactionHash'][:14]) for l in r[:4]])
