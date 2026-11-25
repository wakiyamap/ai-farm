import json, os, time, urllib.request
URL = os.environ["RPC_RELAY_URL"] + "/bsc?lane=research"
def rpc(method, params=None):
    body = json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params or []}).encode()
    req = urllib.request.Request(URL, data=body, headers={"content-type":"application/json"})
    for i in range(2):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                d = json.loads(r.read())
            if "error" in d: return "ERR:"+d["error"].get("message","?")[:60]
            return d["result"]
        except Exception: time.sleep(2)
    return "EXC"
def decstr(h):
    if not h.startswith("0x") or len(h)<130: return h[:24]
    hh=h[2:]; ln=int(hh[64:128],16)
    return bytes.fromhex(hh[128:128+ln*2]).decode("utf8","replace")
out={}
for a in ["0x8bc070bedab741406f4b1eb65a72bee27894b689","0xa5dbeaf16fc031eae92175974f8d0a439be4ad17",
"0x28e2ea090877bf75740558f6bfb36a5ffee9e9df","0x22da1810b194ca018378464a58f6ac2b10c9d244"]:
    r=rpc("eth_call",[{"to":a,"data":"0x06fdde03"},"latest"])
    out[a]= decstr(r) if isinstance(r,str) else r
    print(a,out[a],flush=True)
CAKE="0x0E09FaBB73Bd3Ade0a17ECC321fD13a19e81cE82"
head=int(rpc("eth_blockNumber"),16)
T0="0x"+"ddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
a=head-125
logs=rpc("eth_getLogs",[{"address":CAKE,"topics":[T0],"fromBlock":hex(a),"toBlock":hex(head-1)}])
out["cake_transfers_125_blocks"]= len(logs) if logs is not None else "ERR"
print("cake 125blk:",out["cake_transfers_125_blocks"])
json.dump(out, open("scratch/bsc-pin2-48d09.json","w"), indent=1)
