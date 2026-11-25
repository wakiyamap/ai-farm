"""Sample tx.from + tx.to of the last 12 LEVAMM trades per AMM (logs from yb-493c-count.py)."""
import json, subprocess, collections

RPC = "/srv/farm/ws/tools/rpc.py"


def call(method, params):
    o = subprocess.run(["python3", RPC, "ethereum", method, json.dumps(params), "--lane", "research"],
                       capture_output=True, text=True).stdout
    return json.loads(o).get("result")


logs = json.load(open("/srv/farm/ws/scratch/yb-493c-logs.json"))
per = collections.defaultdict(list)
for l in logs:
    per[l["address"].lower()].append(l)
allc = collections.Counter()
for amm, ev in per.items():
    ev = sorted(ev, key=lambda l: int(l["blockNumber"], 16))[-12:]
    c = collections.Counter()
    for l in ev:
        t = call("eth_getTransactionByHash", [l["transactionHash"]])
        k = (t["from"], t["to"], t["input"][:10])
        c[k] += 1
        allc[(t["from"], t["to"])] += 1
    print(amm, c.most_common(5))
print("ALL", allc.most_common(15))
# one example tx per top sender
