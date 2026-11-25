#!/usr/bin/env python3
"""Phase 10c helper.

  cfg-10c.py dryrun <new farm-watchdog> <gate-status.json>   what the live-loss stop sees for every live
                                         bot right now (relay reads, pnl.json baselines). Exits 1 if one
                                         would be stopped at once, so a human decides before install.
  cfg-10c.py apply <gate.json>           add "max_live_loss_usd": 30 (kept if already set; owner/mode kept)
"""
import importlib.machinery
import importlib.util
import json
import os
import sys
import urllib.request

RELAY = "http://127.0.0.1:8545"
LIVE = "/srv/farm/ws/bots/live"
PNL = "/var/lib/farmgate/pnl.json"
GATE_JSON = "/etc/farm/gate.json"


def rpc(chain, method, params):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    req = urllib.request.Request(f"{RELAY}/{chain}?lane=research", data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        out = json.loads(r.read())
    if "error" in out:
        raise RuntimeError(str(out["error"].get("message")))
    return out["result"]


def dryrun(wd_path, status_path):
    loader = importlib.machinery.SourceFileLoader("wd10c", wd_path)
    wd = importlib.util.module_from_spec(importlib.util.spec_from_loader("wd10c", loader))
    loader.exec_module(wd)
    cfg = json.load(open(GATE_JSON, encoding="utf-8"))
    limit = float(cfg.get("max_live_loss_usd", 30))
    pnl = json.load(open(PNL, encoding="utf-8"))
    status = json.load(open(status_path, encoding="utf-8"))
    over = []
    for bot, info in sorted((status.get("live") or {}).items()):
        addr = info["address"]
        chains = wd.manifest_chains(open(f"{LIVE}/{bot}/manifest.yaml", encoding="utf-8").read())
        vals = {}
        for c in chains:
            bal = int(rpc(c, "eth_getBalance", [addr, "latest"]), 16)
            price = int(rpc(c, "eth_call", [{"to": wd.ETH_USD_FEED[c], "data": "0x50d25bcd"}, "latest"]), 16) / 1e8
            usdc, token = 0, (cfg.get("usdc") or {}).get(c)
            if token:
                r = rpc(c, "eth_call", [{"to": token, "data": "0x70a08231" + addr[2:].lower().rjust(64, "0")}, "latest"])
                usdc = int(r, 16) if r and r != "0x" else 0
            vals[c] = (bal, usdc, price)
        loss = wd.live_loss_usd(pnl, bot, vals)
        base = (pnl.get("baseline") or {}).get(bot)
        funded = sum(base.get(c, 0) / 1e18 * vals[c][2] for c in vals) if base else 0
        funded += sum(v / wd.usdc_scale(c) for c, v in ((pnl.get("baseline_usdc") or {}).get(bot) or {}).items() if c in vals)
        if loss is None:
            print(f"  {bot:30} no baseline in pnl.json -> the live-loss stop cannot judge it (reported once)")
            continue
        print(f"  {bot:30} funded {funded:8.2f} USD, loss since promotion {loss:7.2f} USD"
              f"{'  -> WOULD BE STOPPED' if loss > limit else ''}")
        if loss > limit:
            over.append(bot)
    if over:
        sys.exit(f"dryrun: {over} already past the {limit:.0f} USD live-loss stop; nothing was changed. "
                 "Decide (stop it, or re-baseline) before installing")
    print(f"dryrun ok: no live bot past {limit:.0f} USD")


def apply(path):
    cfg = json.load(open(path, encoding="utf-8"))
    if "max_live_loss_usd" in cfg:
        print(f"  gate.json: max_live_loss_usd already {cfg['max_live_loss_usd']}")
        return
    cfg["max_live_loss_usd"] = 30
    st = os.stat(path)
    tmp = path + ".tmp-10c"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)
        f.write("\n")
    os.chown(tmp, st.st_uid, st.st_gid)
    os.chmod(tmp, st.st_mode & 0o7777)
    os.replace(tmp, path)
    print("  gate.json: max_live_loss_usd = 30")


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["dryrun"] and len(a) == 3:
        dryrun(a[1], a[2])
    elif a[:1] == ["apply"] and len(a) == 2:
        apply(a[1])
    else:
        sys.exit(__doc__)
