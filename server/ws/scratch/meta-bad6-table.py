import json, subprocess, glob
net = {r["bot"]: r for r in json.load(open("/srv/farm/ws/scratch/meta-bad6-net.json"))}
snap = json.load(open("/srv/farm/ws/scratch/review-gate-after-72849.json"))["live"]
exp = {}
for line in subprocess.run(["python3", "/srv/farm/ws/scratch/meta-bad6-exp.py"], capture_output=True, text=True).stdout.splitlines():
    j = json.loads(line); exp[j["bot"]] = j
rows = []
tot = {"sends": 0, "won": 0, "lost": 0, "gross": 0.0, "net": 0.0}
for b in open("/srv/farm/ws/scratch/meta-bad6-stopped.txt").read().split():
    res = {"won": 0, "lost": 0, "other": 0}; gross = 0.0
    for f in glob.glob(f"/srv/farm/ws/bots/archive/{b}/logs/*.jsonl"):
        for l in open(f, errors="replace"):
            if '"send_result"' not in l: continue
            try: j = json.loads(l)
            except Exception: continue
            r = j.get("result")
            k = r if r in ("won", "lost") else "other"
            res[k] += 1
            if r == "won": gross += float(j.get("gross_usd") or 0)
    chain = [c for c in snap[b]["balances_usd"] if ":" not in c][0]
    if b in exp:
        e = exp[b]
        px = snap[b]["balances_usd"][chain] / e["funded_native"] if e["funded_native"] else 0
        sends = e["bot_sends_excl_deploy_sweep"]
        n = (e["swept_native"] - e["funded_native"]) * px
        src = "explorer"
    else:
        r = net[b]
        sends = (r["nonce"] or 2) - 2
        n = r.get("net_usd", 0.0)
        src = "alchemy"
    rows.append((b, chain, sends, res["won"], res["lost"], res["other"], round(gross, 2), round(n, 2), src))
    tot["sends"] += sends; tot["won"] += res["won"]; tot["lost"] += res["lost"]; tot["gross"] += gross; tot["net"] += n
print("| bot | chain | 送信数 | 勝ち | 負け | 結果不明 | 勝ちの粗利 USD | 差し引き USD | 出所 |")
print("|---|---|---|---|---|---|---|---|---|")
for r in rows:
    print("| " + " | ".join(str(x) for x in r) + " |")
print(f"| 計 | | {tot['sends']} | {tot['won']} | {tot['lost']} | | {tot['gross']:.2f} | {tot['net']:.2f} | |")
