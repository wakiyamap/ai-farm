"""For each outsider earmark capture (caller not Convex-affiliated), compute seconds after periodFinish+3600 (read at block-1)
and ETH paid to the block's coinbase inside the tx."""
import json, subprocess, sys
CRVP, ETHP = float(sys.argv[2]), float(sys.argv[3])
CONVEX = {"0xabdcac13b637600bc5b954461d769ea531c8ba04", "0x1389388d01708118b497f59521f6943be2541bb7", "0xe4d89e8267d2e8f03f751fa807b3bbdb36729f9a"}
def rpc(m, p):
    r = subprocess.run(["python3", "/srv/farm/ws/tools/rpc.py", "ethereum", m, json.dumps(p), "--lane", "research"], capture_output=True, text=True)
    return json.loads(r.stdout).get("result")
logs = json.load(open(sys.argv[1]))
if isinstance(logs, dict): logs = logs.get("logs", logs.get("result", []))
import collections
bytx = collections.defaultdict(list)
for l in logs:
    bytx[(int(l["blockNumber"], 16), l["transactionHash"])].append(("0x" + l["topics"][2][-40:], int(l["data"], 16) / 1e18, int(l["logIndex"], 16)))
rows = []
for (b, h), tr in sorted(bytx.items()):
    tr.sort(key=lambda x: x[2])
    i = 0
    while i + 3 <= len(tr) - 1:
        c, r = tr[i], tr[i + 1]
        tot = sum(x[1] for x in tr[i:i + 4])
        if tot > 0 and abs(c[1] / tot - 0.005) < 0.0006:
            if c[0] not in CONVEX and c[1] >= 5:
                rows.append((b, h, c[0], r[0], c[1]))
            i += 4
        else:
            i += 1
print("outsider captures >=5 CRV:", len(rows))
for b, h, caller, rew, inc in rows:
    pf = rpc("eth_call", [{"to": rew, "data": "0xebe2b12b"}, hex(b - 1)])
    pf = int(pf, 16) if pf else 0
    blk = rpc("eth_getBlockByNumber", [hex(b), False])
    ts = int(blk["timestamp"], 16); miner = blk["miner"].lower()
    tr = rpc("debug_traceTransaction", [h, {"tracer": "callTracer"}])
    paid = 0
    def walk(c):
        global paid
        if c.get("to", "").lower() == miner and c["type"] == "CALL":
            paid += int(c.get("value", "0x0"), 16)
        for s in c.get("calls", []) or []:
            walk(s)
    walk(tr)
    rc = rpc("eth_getTransactionReceipt", [h])
    gas = int(rc["gasUsed"], 16) * int(rc["effectiveGasPrice"], 16) / 1e18
    base = int(blk.get("baseFeePerGas", "0x0"), 16)
    prio = (int(rc["effectiveGasPrice"], 16) - base) * int(rc["gasUsed"], 16) / 1e18
    print(b, h[:14], "caller", caller[:10], "from", rc["from"][:10], "crv %.1f usd %.2f" % (inc, inc * CRVP), "t-(pf+1h) %ds" % (ts - pf - 3600), "coinbase_paid_usd %.2f" % (paid / 1e18 * ETHP), "gas_usd %.3f prio_usd %.3f" % (gas * ETHP, prio * ETHP), "txidx", int(rc["transactionIndex"], 16))
