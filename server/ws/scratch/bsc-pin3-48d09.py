import json, os, time, urllib.request
URL = os.environ["RPC_RELAY_URL"] + "/bsc?lane=research"
def rpc(method, params=None):
    body = json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params or []}).encode()
    req = urllib.request.Request(URL, data=body, headers={"content-type":"application/json"})
    for i in range(2):
        try:
            with urllib.request.urlopen(req, timeout=40) as r:
                d = json.loads(r.read())
            if "error" in d: return "ERR:"+json.dumps(d["error"])[:100]
            return d["result"]
        except Exception as e: time.sleep(2)
    return "EXC"
head=int(rpc("eth_blockNumber"),16)
addrs=["0x8bc070bedab741406f4b1eb65a72bee27894b689","0xa5dbeaf16fc031eae92175974f8d0a439be4ad17",
"0x28e2ea090877bf75740558f6bfb36a5ffee9e9df","0x22da1810b194ca018378464a58f6ac2b10c9d244"]
import functools
def cs(a):
    # checksum via web3-style: use alchemy's expected? do keccak-based simple: reuse plain '0x'+lower if alnum
    from hashlib import sha3_256
    return a
out={}
for a in addrs:
    r=rpc("alchemy_getAssetTransfers",[{"fromBlock":hex(head-3000),"toBlock":hex(head),"toAddress":a,"category":["erc20"],"maxCount":"0x3","excludeFromAmount":False,"withToken":True}])
    out[a]=r
    print(a, json.dumps(r)[:400], flush=True)
json.dump(out, open("scratch/bsc-pin3-48d09.json","w"), indent=1)
