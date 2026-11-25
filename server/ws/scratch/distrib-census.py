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
head=int(rpc("eth_blockNumber",[]),16)
from_block=head-511000
topic0="0xddc9c30275a04c48091f24199f9c405765de34d979d6847f5b9798a57232d2e5"
total=0; pages=0
a=from_block
while a<=head:
    b=min(a+9999, head)
    logs=rpc("eth_getLogs", [{"fromBlock":hex(a),"toBlock":hex(b),
        "address":["0x3d9819210A31B4DE2A5E6c37681e6624EEFC8af6"],
        "topics":[topic0]}])
    total+=len(logs); pages+=1
    if logs: print("page",hex(a),hex(b),"logs",len(logs),[ (hex(int(l['blockNumber'],16)), l['transactionHash']) for l in logs][:6])
    a=b+1
print(f"head {head} window {from_block}-{head} pages {pages} Distributed events {total}")
