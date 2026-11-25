import json, urllib.request, os, sys
RELAY = os.environ["RPC_RELAY_URL"]
def rpc(method, params, chain="bsc", lane="research"):
    body = json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    req = urllib.request.Request(f"{RELAY}/{chain}?lane={lane}", data=body,
        headers={"content-type":"application/json"})
    r = json.loads(urllib.request.urlopen(req, timeout=60).read())
    if "error" in r: raise SystemExit(f"error: {r['error']}")
    return r["result"]

HEAD = int(rpc("eth_blockNumber", []), 16)
print("head", HEAD)
TOPICS = {
 "Collect": "0x6aaba5d46bfa4cab371e70f31e2a5e8746962de66225491d4317c47bbdbf5eef",
 "Claimed": "0xf7a40077ff7a04c7e61f6f26fb13774259ddf1b6bce9ecf26a8276cdd3992683",
 "Burn":    "0xcc16f5dbb4873280815c1ee09dbd06736cffcc184412cf7a71a0fdb75d397ca5",
 "Minted":  "0x30385c845b448a36257a6a1716e6ad2e1bc2cbe333cde1e69fe849ad6511adfe",
 "Deposit": "0x5548c837ab068cf56a2c2479df0882a4922fd203edb7517321831d95078c5f62",  # Deposit(address,address,uint256)
 "Withdraw":"0x9b1bfa7fa9ee420a16e124f794c35ac9f90472acc99140eb2f6447c714cad8eb",  # Withdraw(address,address,uint256)
 "Transfer":"0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523efef",
}
import hashlib
def keccak(sig):
    # verify my two guessed Deposit/Withdraw hashes with cast keccak externally; here just placeholder
    return None
out = {}
pages = [(HEAD-125*i-124, HEAD-125*i) for i in range(10,0,-1)]
for name, t0 in TOPICS.items():
    if t0 is None: continue
    total = 0; per = []
    for a,b in pages:
        logs = rpc("eth_getLogs", [{"fromBlock":hex(a),"toBlock":hex(b),"topics":[t0]}])
        per.append(len(logs)); total += len(logs)
    out[name] = {"total_1250blk": total, "per_page": per}
    print(name, total, per)
json.dump({"head": HEAD, "census": out}, open("scratch/bsc-poke-census.json","w"), indent=1)
