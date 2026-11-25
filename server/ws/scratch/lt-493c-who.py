import json, subprocess, sys

RPC = "/srv/farm/ws/tools/rpc.py"


def call(chain, method, params):
    out = subprocess.run(["python3", RPC, chain, method, json.dumps(params), "--lane", "research"],
                         capture_output=True, text=True).stdout
    return json.loads(out).get("result")


logs = json.load(open("/srv/farm/ws/scratch/lt-493c-eth-lm.json"))
logs = logs.get("result", logs)
for l in logs:
    tx = call("ethereum", "eth_getTransactionByHash", [l["transactionHash"]])
    rc = call("ethereum", "eth_getTransactionReceipt", [l["transactionHash"]])
    blk = call("ethereum", "eth_getBlockByNumber", [l["blockNumber"], False])
    gas_eth = int(rc["gasUsed"], 16) * int(rc["effectiveGasPrice"], 16) / 1e18
    print(int(l["blockNumber"], 16), int(blk["timestamp"], 16), "from", tx["from"], "to", tx["to"],
          "sel", tx["input"][:10], "gasUsed", int(rc["gasUsed"], 16), "gas_eth %.6f" % gas_eth,
          "nlogs", len(rc["logs"]))

# auction params of the three adapters
for a in ["0x42fc033435f4640affed1d5cf6f3bbe240d081af", "0x0ad07431771021bb861de576c964b5e00b02b3bf",
          "0x5e4837e4672e8f84b53cf884aadea0e858b40d36"]:
    r = {}
    for name, sel in [("duration", "0x"), ]:
        pass
    for name, sig in [("getAuctionDuration", "getAuctionDuration()"), ("getInitialPriceMultiplier", "getInitialPriceMultiplier()"),
                      ("getMinPriceMultiplier", "getMinPriceMultiplier()"), ("getLeverageToken", "getLeverageToken()")]:
        sel = subprocess.run(["/opt/foundry/bin/cast", "sig", sig], capture_output=True, text=True).stdout.strip()
        r[name] = call("ethereum", "eth_call", [{"to": a, "data": sel}, "latest"])
    print(a, {k: (int(v, 16) if v and k != "getLeverageToken" else v) for k, v in r.items()})
