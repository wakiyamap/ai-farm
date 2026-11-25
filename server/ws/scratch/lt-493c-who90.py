import json, subprocess

RPC = "/srv/farm/ws/tools/rpc.py"


def call(method, params):
    o = subprocess.run(["python3", RPC, "ethereum", method, json.dumps(params), "--lane", "research"],
                       capture_output=True, text=True).stdout
    return json.loads(o).get("result")


logs = json.load(open("/srv/farm/ws/scratch/lt-493c-hist-logs.json"))
for l in logs:
    b = int(l["blockNumber"], 16)
    if b < 25777999 or not l["topics"][1].endswith("98c4e43e3bde7b649e5aa2f88de1658e8d3ed1bf"):
        continue
    w = [int(l["data"][2 + 64 * i:2 + 64 * (i + 1)], 16) for i in range(8)]
    t = call("eth_getTransactionByHash", [l["transactionHash"]])
    r = call("eth_getTransactionReceipt", [l["transactionHash"]])
    gas = int(r["gasUsed"], 16) * int(r["effectiveGasPrice"], 16) / 1e18
    print(b, t["from"], t["to"], "eqloss %.6f" % ((w[2] - w[6]) / 1e18), "debtAdded %.3f" % ((w[5] - w[1]) / 1e18),
          "gas %.6f" % gas, l["transactionHash"])
