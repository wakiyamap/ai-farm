import json, sys, subprocess, collections
inc = json.load(open(sys.argv[1]))
CRV, ETH = float(sys.argv[2]), float(sys.argv[3])
by = collections.defaultdict(list)
for b, h, to, a, tot in inc:
    by[to].append((b, h, a))
out = []
for caller, rows in sorted(by.items(), key=lambda kv: -len(kv[1]))[:8]:
    rows.sort(key=lambda r: r[2])
    pick = [rows[0], rows[len(rows) // 2], rows[-1]] if len(rows) >= 3 else rows
    for b, h, a in pick:
        r = subprocess.run(["python3", "/srv/farm/ws/tools/rpc.py", "ethereum", "eth_getTransactionReceipt", json.dumps([h]), "--lane", "research"], capture_output=True, text=True)
        try:
            rc = json.loads(r.stdout)["result"]
        except Exception:
            print("fail", h); continue
        gas = int(rc["gasUsed"], 16) * int(rc["effectiveGasPrice"], 16) / 1e18
        logs = len(rc["logs"])
        print(caller[:10], "from", rc["from"][:10], "to", (rc["to"] or "")[:10], "blk", b, "crv %.2f" % a, "usd %.2f" % (a * CRV), "gasUsed", int(rc["gasUsed"], 16), "gwei %.2f" % (int(rc["effectiveGasPrice"], 16) / 1e9), "gasusd %.3f" % (gas * ETH), "logs", logs, h)
