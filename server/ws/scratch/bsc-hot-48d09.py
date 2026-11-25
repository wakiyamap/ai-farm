import json, os, time, urllib.request
URL = os.environ["RPC_RELAY_URL"] + "/bsc?lane=research"
def rpc(method, params=None):
    body = json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params or []}).encode()
    req = urllib.request.Request(URL, data=body, headers={"content-type":"application/json"})
    for i in range(3):
        try:
            with urllib.request.urlopen(req, timeout=40) as r:
                d = json.loads(r.read())
            if "error" in d: time.sleep(1); continue
            return d["result"]
        except Exception: time.sleep(2)
    return None
T0="0x"+"ddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
hot=["0x8bc070bedab741406f4b1eb65a72bee27894b689","0xa5dbeaf16fc031eae92175974f8d0a439be4ad17","0x28e2ea090877bf75740558f6bfb36a5ffee9e9df","0x22da1810b194ca018378464a58f6ac2b10c9d244"]
head=int(rpc("eth_blockNumber"),16)
a=head-125
logs=rpc("eth_getLogs",[{"topics":[T0],"fromBlock":hex(a),"toBlock":hex(head-1)}])
print("page logs:",len(logs) if logs else "ERR")
json.dump(logs, open("scratch/bsc-hotlogs-48d09.json","w"))
want={h[-40:]:h for h in hot}
picks={}
for L in logs or []:
    if len(L["topics"])>=3:
        r=L["topics"][2][26:].lower()
        if r in want and want[r] not in picks:
            picks[want[r]]={"hash":L["transactionHash"],"token":L["address"],"from":L["topics"][1][26:].lower()}
print(json.dumps(picks,indent=1))
json.dump(picks, open("scratch/bsc-hotpicks-48d09.json","w"))
