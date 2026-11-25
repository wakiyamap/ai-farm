"""Seamless LeverageManager (ethereum) Rebalance history since deployment.
Equity loss of the LT per rebalance = what the rebalancer took (gross, debt-asset units)."""
import json, subprocess, collections

RPC = "/srv/farm/ws/tools/rpc.py"
LM = "0x5C37EB148D4a261ACD101e2B997A0F163Fb3E351"
T0 = "0x1ece35fa7611d2dfc7e11d022888a20c4987d6ededbb34a26c93fd53f2073899"
START, HEAD = 23471226, 26425999


def call(method, params):
    o = subprocess.run(["python3", RPC, "ethereum", method, json.dumps(params), "--lane", "research"],
                       capture_output=True, text=True).stdout
    j = json.loads(o)
    if "error" in j:
        raise RuntimeError(j["error"])
    return j["result"]


def cast(*a):
    return subprocess.run(["/opt/foundry/bin/cast", *a], capture_output=True, text=True).stdout.strip()


logs = []
step = 250000
b = START
while b <= HEAD:
    e = min(HEAD, b + step - 1)
    logs += call("eth_getLogs", [{"address": LM, "topics": [T0], "fromBlock": hex(b), "toBlock": hex(e)}])
    b = e + 1
json.dump(logs, open("/srv/farm/ws/scratch/lt-493c-hist-logs.json", "w"))

tokens = collections.defaultdict(list)
for l in logs:
    w = [int(l["data"][2 + 64 * i:2 + 64 * (i + 1)], 16) for i in range(8)]
    tok = "0x" + l["topics"][1][-40:]
    tokens[tok].append((int(l["blockNumber"], 16), (w[2] - w[6]) / 1e18, w[1] / 1e18, w[5] / 1e18, l["transactionHash"]))

for tok, ev in tokens.items():
    coll = call("eth_call", [{"to": LM, "data": cast("calldata", "getLeverageTokenCollateralAsset(address)", tok)}, "latest"])
    debt = call("eth_call", [{"to": LM, "data": cast("calldata", "getLeverageTokenDebtAsset(address)", tok)}, "latest"])
    print("token", tok, "coll", "0x" + coll[-40:], "debt", "0x" + debt[-40:], "n", len(ev))
    for blk in (HEAD - 7200 * 30, HEAD - 7200 * 90, HEAD - 7200 * 180, START):
        sel = [x for x in ev if x[0] >= blk]
        days = (HEAD - max(blk, START)) / 7200
        g = sum(x[1] for x in sel)
        print("   since %d (%.0f d): n=%d gross_debt_units=%.5f per_day=%.6f" % (blk, days, len(sel), g, g / days))
    for x in ev[-12:]:
        print("   ", x[0], "eqloss %.6f" % x[1], "debt %.3f->%.3f" % (x[2], x[3]), x[4][:14])
