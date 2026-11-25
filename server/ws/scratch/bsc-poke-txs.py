import json, urllib.request, os
RELAY = os.environ["RPC_RELAY_URL"]
def rpc(method, params, chain="bsc", lane="research"):
    body = json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    req = urllib.request.Request(f"{RELAY}/{chain}?lane={lane}", data=body,
        headers={"content-type":"application/json"})
    r = json.loads(urllib.request.urlopen(req, timeout=90).read())
    if "error" in r: print("ERR", r["error"]); return None
    return r["result"]
TXS = {
 "Claimed1": "0x7b783e74fc64268f90003115ca863677de77eee4bcafd86eb69f6e1b9ce5d3f8",
 "Claimed2": "0x07fe3e8063a31899dbb33cd7bcceac3f9a038b5fa45d6d757ec3ae2b75fd808e",
 "Deposit1": "0xd1e2c995ce430e4f1dff0142fa221dc9eae326672186cc48636dc01b1cc2ef73",
 "Deposit2": "0x0ce74740503d97ae203a2763151806c000c8faf0aba0fdac17ea73d506beb26b",
 "Withdraw1": "0x83844fb10e17bbb43fc1d4d1a6a9e24000e8f1a5a70abb493606367e14d6616b",
 "Burn1":    "0xaa9c374c9c3de3f7244557ab1b5f4f5d40891cc1d343a0f8ad31e850a9b2281e",
}
out = {}
for k, h in TXS.items():
    tx = rpc("eth_getTransactionByHash", [h])
    out[k] = {"from": tx["from"], "to": tx["to"], "input_sel": tx["input"][:10], "input_len": len(tx["input"])//2, "value": tx["value"], "gas_used": None}
    print(k, "from", tx["from"], "to", tx["to"], "sel", tx["input"][:10], "ilen", len(tx["input"])//2)
    r = rpc("eth_getTransactionReceipt", [h])
    if r: out[k].update({"gasUsed": r.get("gasUsed"), "status": r.get("status")})
json.dump(out, open("scratch/bsc-poke-txs.json","w"), indent=1)
