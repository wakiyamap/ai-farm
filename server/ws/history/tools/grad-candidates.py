#!/usr/bin/env python3
"""Graduation candidates (decision 2026-11-24-graduate-and-builder-focus.md, section 1).

Read-only. For every live `trial-*` bot (from `gate status`):
  hours live   = now - mtime of bots/live/<id>/state/executor.json (written by the gate at promote)
  funded_usd   = native + USDC sent from the intermediate wallet to the bot address
                 (alchemy_getAssetTransfers through the relay, top-ups included),
                 native valued at the current price (intermediate usd / intermediate native balance)
  net_usd      = gate status wallet value - funded_usd   (same basis as the watchdog)
  won / sent   = send result lines in logs/*.jsonl ("result" or "send_result" == "won")
Candidate = hours >= 72 and net >= +1 and won >= 3. Ethereum is excluded by the decision.
"(grad live|paper|archive)" = bots/<state>/grad-<id> already exists (not an open candidate).
If transfers cannot be read on a chain, funded falls back to manifest capital_usd (marked "~").

Usage: python3 tools/grad-candidates.py [--all] [--json]
Cost: one getBalance per chain + one alchemy_getAssetTransfers per bot (~150 CU each).
"""
import glob, json, os, re, subprocess, sys, time

WS = "/srv/farm/ws"
RPC = [sys.executable, f"{WS}/tools/rpc.py"]
INTER = "0x915bd260dCb166f86a499D5fDb3775b5bec70427"


def sh(args):
    r = subprocess.run(args, capture_output=True, text=True, timeout=120)
    return r.returncode, r.stdout


def rpc(chain, method, params):
    code, out = sh(RPC + [chain, method, json.dumps(params), "--lane", "research"])
    if code != 0:
        return None
    try:
        return json.loads(out).get("result")
    except Exception:
        return None


def manifest_capital(path):
    try:
        for line in open(path):
            m = re.match(r"\s*capital_usd:\s*([0-9.]+)", line)
            if m:
                return float(m.group(1))
    except OSError:
        pass
    return None


def sends(bot_dir):
    won = sent = 0
    for f in glob.glob(f"{bot_dir}/logs/*.jsonl"):
        try:
            fh = open(f, errors="replace")
        except OSError:
            continue
        for line in fh:
            if "won" not in line and "lost" not in line and "send_result" not in line:
                continue
            try:
                d = json.loads(line)
            except Exception:
                continue
            if not isinstance(d, dict):
                continue
            is_send = d.get("ev") == "send_result" or d.get("event") == "send_result" or "send_result" in d
            if not is_send:
                continue
            res = d.get("result", d.get("send_result"))
            if isinstance(res, dict):
                res = res.get("result")
            sent += 1
            if res == "won":
                won += 1
    return won, sent


def main():
    show_all = "--all" in sys.argv
    as_json = "--json" in sys.argv
    code, out = sh(["gate", "status"])
    st = json.loads(out)
    inter = st["intermediate_balances_usd"]
    prices = {}

    def price(chain):
        if chain not in prices:
            bal = rpc(chain, "eth_getBalance", [st.get("intermediate", INTER), "latest"])
            usd = inter.get(chain)
            prices[chain] = (usd / (int(bal, 16) / 1e18)) if bal and usd and int(bal, 16) > 0 else None
        return prices[chain]

    rows = []
    now = time.time()
    for bid, b in sorted(st["live"].items()):
        if not bid.startswith("trial-"):
            continue
        d = f"{WS}/bots/live/{bid}"
        ex = f"{d}/state/executor.json"
        hours = (now - os.path.getmtime(ex)) / 3600 if os.path.exists(ex) else None
        chains = sorted({k.split(":")[0] for k in b["balances_usd"]})
        wallet = sum(b["balances_usd"].values())
        funded, exact = 0.0, True
        for c in chains:
            if c == "ethereum":
                continue
            tr = rpc(c, "alchemy_getAssetTransfers", [{"fromBlock": "0x0", "toBlock": "latest",
                     "fromAddress": st.get("intermediate", INTER), "toAddress": b["address"],
                     "category": ["external", "erc20"]}])
            p = price(c)
            if tr is None or p is None:
                exact = False
                break
            for t in tr.get("transfers", []):
                v = float(t.get("value") or 0)
                if t["category"] == "external":
                    funded += v * p
                elif (t.get("asset") or "").upper().startswith("USDC"):
                    funded += v
        if not exact or funded == 0:
            cap = manifest_capital(f"{d}/manifest.yaml")
            funded, exact = (cap or 0.0), False
        won, sent = sends(d)
        net = wallet - funded
        cand = hours is not None and hours >= 72 and net >= 1 and won >= 3 and "ethereum" not in chains
        gid = "grad-" + bid[len("trial-"):]
        grad = next((s for s in ("live", "paper", "archive") if os.path.isdir(f"{WS}/bots/{s}/{gid}")), None)
        rows.append({"bot": bid, "chains": chains, "hours": round(hours or 0, 1), "wallet_usd": round(wallet, 2),
                     "funded_usd": round(funded, 2), "funded_exact": exact, "net_usd": round(net, 2),
                     "won": won, "sent": sent, "candidate": cand, "grad": grad})
    rows.sort(key=lambda r: (not r["candidate"], -r["net_usd"]))
    if as_json:
        for r in rows:
            if show_all or r["candidate"] or r["net_usd"] > 0:
                print(json.dumps(r))
        return
    print(f"{'bot':38} {'h':>6} {'wallet':>7} {'funded':>8} {'net':>7} {'won/sent':>9} cand")
    for r in rows:
        if not (show_all or r["candidate"] or r["net_usd"] > 0):
            continue
        f = f"{r['funded_usd']:.2f}" + ("" if r["funded_exact"] else "~")
        print(f"{r['bot']:38} {r['hours']:6.1f} {r['wallet_usd']:7.2f} {f:>8} {r['net_usd']:7.2f} "
              f"{str(r['won']) + '/' + str(r['sent']):>9} {'YES' if r['candidate'] else ''}"
              f"{' (grad ' + r['grad'] + ')' if r['grad'] else ''}")
    print(f"# {sum(r['candidate'] and not r['grad'] for r in rows)} open candidates "
          f"({sum(r['candidate'] for r in rows)} pass the rule) of {len(rows)} live trial bots; "
          f"rule: >=72 h live, net >= +1 USD, >=3 won; '~' = funded from manifest capital_usd; "
          f"'(grad archive)' = read bots/archive/grad-<id>/ARCHIVE.md before rebuilding")


if __name__ == "__main__":
    main()
