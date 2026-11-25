"""Part 2: identify adapter events, takers, gas, prices. Scout run bea55ede."""
import json, subprocess

RPC = "/srv/farm/ws/tools/rpc.py"
LM = "0x5C37EB148D4a261ACD101e2B997A0F163Fb3E351"
ADP = "0x42fc033435f4640affed1d5cf6f3bbe240d081af"
WADP = "0x5e4837e4672e8f84b53cf884aadea0e858b40d36"
CALLER = "0x000000000000000000000000000000000000b00b"


def call(method, params):
    o = subprocess.run(["python3", RPC, "ethereum", method, json.dumps(params)],
                       capture_output=True, text=True)
    j = json.loads(o.stdout)
    if "error" in j:
        raise RuntimeError(str(j["error"])[:200])
    return j["result"]


def keccak(sig):
    o = subprocess.run(["/opt/foundry/bin/cast", "keccak", sig], capture_output=True, text=True)
    return o.stdout.strip()


def calldata(sig, arg=""):
    o = subprocess.run(["/opt/foundry/bin/cast", "calldata", sig, arg], capture_output=True, text=True)
    return o.stdout.strip()


head = int(call("eth_blockNumber", []), 16)
f7 = head - 50400

sigs = {
    "Take(address,uint256,uint256)": keccak("Take(address,uint256,uint256)"),
    "AuctionEnded()": keccak("AuctionEnded()"),
    "LeverageTokenCreated(address,address,address,(address,address,uint256,uint256))":
        keccak("LeverageTokenCreated(address,address,address,(address,address,uint256,uint256))"),
}
print("keccak:", json.dumps(sigs, indent=1))

# adapter 7d logs with taker decoding for Take topic
for name, adp in (("0x42fc", ADP), ("0x5e48", WADP)):
    logs = call("eth_getLogs", [{"address": adp, "fromBlock": hex(f7), "toBlock": hex(head)}])
    print("\nadapter", name, "7d logs:", len(logs))
    t0s = {}
    for l in logs:
        t0s.setdefault(l["topics"][0], []).append(l)
    for t0, ls in t0s.items():
        lbl = next((k for k, v in sigs.items() if v == t0), "UNKNOWN")
        print("  topic0", t0[:20], lbl, "n=", len(ls))
        if lbl.startswith("Take"):
            for l in ls:
                taker = "0x" + l["topics"][1][-40:] if len(l["topics"]) > 1 else "?"
                w = [int(l["data"][2 + 64 * i:2 + 64 * (i + 1)], 16) for i in range(2)]
                print("    blk", int(l["blockNumber"], 16), "taker", taker,
                      "amountIn %.5f amountOut %.5f" % (w[0] / 1e18, w[1] / 1e18), "tx", l["transactionHash"])

# receipts of the 4 rebalance txs: from, gasUsed, effectiveGasPrice
txs = {
    "0x837651da2008538adf738a7ea865a0dddce96e441df9827236e70b96e2db4df8": "ce93 reb1",
    "0x4d1014b1116fe4a2a468e8739e2bf0591df83f88915cdd35b01517e87232a52f": "ce93 reb2",
    "0x05daba3c0480b28a6b21a9b76e7c25fc38f4ff5edcb338881425e1838d1190b7": "98c4 reb (eqLoss neg)",
    "0xb3e3b6c5125ab9a74a5669cc61128221d828f4a3dcf5504f01e1df643d1be309": "98c4 reb",
}
for h, lab in txs.items():
    r = call("eth_getTransactionReceipt", [h])
    if r is None:
        print(lab, "receipt null"); continue
    gas = int(r["gasUsed"], 16) * int(r["effectiveGasPrice"], 16) / 1e18
    print(lab, "from", r["from"], "gasUsed", int(r["gasUsed"], 16), "gasETH %.6f" % gas, "status", r["status"])

# new LTs created in last 7d
ltc = call("eth_getLogs", [{"address": LM, "topics": [sigs["LeverageTokenCreated(address,address,address,(address,address,uint256,uint256))"]], "fromBlock": hex(f7), "toBlock": hex(head)}])
print("\nLeverageTokenCreated 7d: n =", len(ltc), ["0x" + l['topics'][1][-8:] for l in ltc])

# isAuctionValid on both adapters, fresh-addr take revert data
for name, adp in (("0x42fc", ADP), ("0x5e48", WADP)):
    v = call("eth_call", [{"to": adp, "data": calldata("isAuctionValid()")}, "latest"])
    print(name, "isAuctionValid:", v)
    o = subprocess.run(["python3", RPC, "ethereum", "eth_call",
                        json.dumps([{"from": CALLER, "to": adp, "data": calldata("take(uint256)", "1000000000000000")}, "latest"])],
                       capture_output=True, text=True)
    j = json.loads(o.stdout)
    if "error" in j:
        d = j["error"].get("data", "")
        print(name, "take from fresh addr reverts, data:", str(d)[:74])
    else:
        print(name, "take from fresh addr OK:", str(j["result"])[:20])
