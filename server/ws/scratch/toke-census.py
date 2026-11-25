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
print("topic0", t0)
head=int(rpc("eth_blockNumber",[]),16)
lo=head-131000
logs=[]
a=lo
while a<=head:
    b=min(a+9999,head)
    r=rpc("eth_getLogs",[{"fromBlock":hex(a),"toBlock":hex(b),"address":[mgr],"topics":[t0]}])
    logs+=r
    a=b+1
print("CycleRolloverStarted events in 90d:", len(logs))
for l in logs[-6:]:
    print(hex(int(l["blockNumber"],16)), l["transactionHash"], l["data"][:40])
# also getCurrentCycle view call
sel="0x"+subprocess.check_output(["cast","keccak","getCurrentCycle()"],text=True).strip()[2:][:8]
res=rpc("eth_call",[{"to":mgr,"data":sel},"latest"])
print("getCurrentCycle()", sel, "->", res)
