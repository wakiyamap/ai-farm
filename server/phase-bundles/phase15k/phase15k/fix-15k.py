#!/usr/bin/env python3
"""One-time correction of the 11-21 one-shot sweep (phase 15k).

  fix-15k.py check <state dir>
  fix-15k.py apply <state dir>

oneshot-bundles-rebalance-ethereum was swept at 2026-11-20T22:40Z (UTC day 2026-11-20). Its
sweep_usdc record carries usd null for 34.614241 USDC, so realized_usd shows -3.7294 (the native leg
only) instead of +30.8848.
- gate.log: append one record {"op": "sweep_usdc_fix", "bot": ..., "usd": 34.6142, ...} (once).
- pnl.json: if its day is still 2026-11-20 and realized_usd[bot] is -3.7294, add 34.6142 (the
  daily-loss guard then counts no loss for it). After the UTC day has rolled, realized_usd is already
  reset and only the gate.log record is written.
Run as farmgate (the files are farmgate's). Writes pnl.json the way the gate does (tmp + rename).
"""
import datetime as dt
import json
import os
import sys

BOT = "oneshot-bundles-rebalance-ethereum"
DAY = "2026-11-20"
NATIVE_USD = -3.7294
USDC = 34614241
FIX_USD = 34.6142
TX = "0x100168ae54ab07c12fbde0df9f18589ecb86418ba8b1415da4b1e7a45722561f"


def main(a):
    if len(a) != 2 or a[0] not in ("check", "apply"):
        raise SystemExit(__doc__)
    log_path, pnl_path = os.path.join(a[1], "gate.log"), os.path.join(a[1], "pnl.json")
    recs = []
    with open(log_path, encoding="utf-8") as f:
        for line in f:
            try:
                recs.append(json.loads(line))
            except ValueError:
                pass
    mine = [r for r in recs if isinstance(r, dict) and r.get("bot") == BOT]
    su = [r for r in mine if r.get("op") == "sweep_usdc"]
    if not su or su[-1].get("usdc") != USDC or su[-1].get("usd") is not None or su[-1].get("txHash") != TX:
        raise SystemExit(f"gate.log: the sweep_usdc record of {BOT} is not the expected one; nothing was changed")
    done_log = any(r.get("op") == "sweep_usdc_fix" for r in mine)
    with open(pnl_path, encoding="utf-8") as f:
        p = json.load(f)
    cur = (p.get("realized_usd") or {}).get(BOT)
    fix_pnl = p.get("day") == DAY and cur is not None and abs(cur - NATIVE_USD) < 1e-6
    print(f"  gate.log: sweep_usdc_fix {'already there' if done_log else 'to append'} (+{FIX_USD} USD)")
    if p.get("day") != DAY:
        print(f"  pnl.json: day is {p.get('day')}, realized_usd was reset at 00:00 UTC; nothing to change")
    elif fix_pnl:
        print(f"  pnl.json: realized_usd[{BOT}] {cur} -> {round(cur + FIX_USD, 4)}")
    else:
        print(f"  pnl.json: realized_usd[{BOT}] is {cur}; already corrected or changed, left alone")
    if a[0] == "check":
        return
    if not done_log:
        rec = {"op": "sweep_usdc_fix", "bot": BOT, "chain": "ethereum", "usdc": USDC, "usd": FIX_USD,
               "txHash": TX, "note": "15k: USDC swept from a bot funded with native only was booked as usd null",
               "at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
               "by": os.environ.get("SUDO_USER", "?"), "role": "phase15k"}
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, separators=(",", ":")) + "\n")
    if fix_pnl:
        p["realized_usd"][BOT] = round(cur + FIX_USD, 4)
        tmp = pnl_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(p, f)
        os.replace(tmp, pnl_path)
    print("fix-15k: apply ok")


if __name__ == "__main__":
    main(sys.argv[1:])
