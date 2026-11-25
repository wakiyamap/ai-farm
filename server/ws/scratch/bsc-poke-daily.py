import json, urllib.request, os
RELAY = os.environ["RPC_RELAY_URL"]
def rpc(method, params, chain="bsc", lane="research"):
    body = json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    req = urllib.request.Request(f"{RELAY}/{chain}?lane={lane}", data=body,
        headers={"content-type":"application/json"})
    r = json.loads(urllib.request.urlopen(req, timeout=90).read())
    if "error" in r: print("ERR", r["error"]); return None
    return r["result"]
HEAD = int(rpc("eth_blockNumber", []), 16)
T = {
 "Collect": "0x6aaba5d46bfa4cab371e70f31e2a5e8746962de66225491d4317c47bbdbf5eef",
 "Claimed": "0xf7a40077ff7a04c7e61f6f26fb13774259ddf1b6bce9ecf26a8276cdd3992683",
 "Burn":    "0xcc16f5dbb4873280815c1ee09dbd06736cffcc184412cf7a71a0fdb75d397ca5",
 "Deposit": "0x5548c837ab068cf56a2c2479df0882a4922fd203edb7517321831d95078c5f62",
 "Withdraw":"0x9b1bfa7fa9ee420a16e124f794c35ac9f90472acc99140eb2f6447c714cad8eb",
}
out = {"head": HEAD}
for name, t0 in T.items():
    logs = []
    for i in range(10, 0, -1):
        a, b = HEAD - 5000*i - 4999, HEAD - 5000*i
        r = rpc("eth_getLogs", [{"fromBlock":hex(a),"toBlock":hex(b),"topics":[t0]}])
        if r is None: print(name,"page fail",a); continue
        logs.extend(r)
    out[name] = {"count_50000blk": len(logs), "emitters": sorted({l["address"].lower() for l in logs}),
                 "sample": [{"h": l["transactionHash"], "blk": int(l["blockNumber"],16), "addr": l["address"], "topics": l["topics"], "data": l["data"][:80]} for l in logs[-3:]]}
    print(name, len(logs), "emitters:", len(out[name]["emitters"]), out[name]["emitters"][:5])
json.dump(out, open("scratch/bsc-poke-daily.json","w"), indent=1)
