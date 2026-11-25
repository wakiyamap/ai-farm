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
mgr="0x59170d9d1d3db8ac3539c6705fb38c735af9f4c9"
t0="0x"+subprocess.check_output(["cast","keccak","CycleRolloverStarted(uint256)"],text=True).strip()[2:][:64]
head=26373991
for k in [2,3,4,5,6,8,10,12]:
    lo=head-131000*k
    r=rpc("eth_getLogs",[{"fromBlock":hex(lo),"toBlock":hex(lo+9999),"address":[mgr],"topics":[t0]}])
    print(f"k={k} blocks {lo}-{lo+9999} ({head-lo:,} back):", len(r), [(hex(int(l['blockNumber'],16)),l['transactionHash']) for l in r[:3]])
