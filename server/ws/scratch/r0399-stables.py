"""Screen stablecoins for below-peg episodes (DefiLlama 2h prices, 30 d). Holding-frame view: buy at <= ENTRY, sell at >= EXIT, max hold 7 d."""
import json, subprocess, sys, time
ids = sys.argv[1].split(",")
START = int(sys.argv[2]); ENTRY = float(sys.argv[3]); EXIT = float(sys.argv[4])
PERIOD = sys.argv[5] if len(sys.argv) > 5 else "2h"
out = {}
for cid in ids:
    url = "https://coins.llama.fi/chart/coingecko:%s?start=%d&span=360&period=%s" % (cid, START, PERIOD)
    r = subprocess.run(["curl", "-s", url], capture_output=True, text=True)
    try:
        d = json.loads(r.stdout)["coins"]["coingecko:" + cid]
    except Exception:
        print(cid, "missing"); continue
    p = [(x["timestamp"], x["price"]) for x in d["prices"]]
    out[cid] = p
    lo = min(v for _, v in p); below = sum(1 for _, v in p if v < 0.995)
    # simple episode sim: enter at first point <= ENTRY when flat, exit at first later point >= EXIT or after 7 d (at that price)
    trades = []; i = 0
    while i < len(p):
        t0, v0 = p[i]
        if v0 <= ENTRY:
            j = i + 1
            while j < len(p) and p[j][1] < EXIT and p[j][0] - t0 < 7 * 86400:
                j += 1
            if j >= len(p):
                trades.append((t0, v0, None, None)); break
            trades.append((t0, v0, p[j][0], p[j][1])); i = j + 1
        else:
            i += 1
    closed = [t for t in trades if t[2]]
    pnl = sum((t[3] / t[1] - 1) * 100 for t in closed)
    print("%-22s n=%3d min=%.4f last=%.4f pts<0.995=%3d trades=%d open=%d pnl_per_100usd=%.2f %s" % (d.get("symbol", cid), len(p), lo, p[-1][1], below, len(closed), len(trades) - len(closed), pnl,
          ["%s %.4f->%.4f %.1fh" % (time.strftime("%m-%d", time.gmtime(t[0])), t[1], t[3], (t[2] - t[0]) / 3600) for t in closed][:4]))
json.dump(out, open("/srv/farm/ws/scratch/r0399-stables-series.json", "w"))
