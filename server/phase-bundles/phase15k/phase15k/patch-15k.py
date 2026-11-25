#!/usr/bin/env python3
"""Phase 15k text patches: USDC a bot earned counts as profit when its sweep is booked.

  patch-15k.py check <gate-ctl> <farm-dash>
  patch-15k.py apply <gate-ctl> <farm-dash> <outdir>

gate-ctl (sweep and settle_usdc_in_flight)
  The USDC leg of a sweep booked PnL only against baseline_usdc, i.e. only for bots the gate had
  funded with USDC principal. A bot funded with native only that earned USDC (the one-shot
  oneshot-bundles-rebalance-ethereum, +34.61 USDC on 11-21) got `usd: null` on its sweep_usdc record,
  while its native leg booked the gas it spent: the sweep showed -3.73 USD instead of +30.88, and the
  daily-loss guard (realized_usd) counted that as a loss.
  Now: a bot the gate funded (it has a native baseline) and with no USDC baseline on that chain has a
  USDC baseline of 0, so all the USDC swept back is profit.

farm-dash (pnl_history, swept_total)
  The swept PnL summed only `sweep` records (native). It now also sums sweep_usdc,
  sweep_usdc_inflight and the one-time correction record sweep_usdc_fix (fix-15k.py).
"""
import os
import sys

GATE = [
("sweep: USDC baseline 0 for a bot funded with native only",
'''                unsure.pop(chain + ":usdc", None)
                swept[chain + ":usdc"] = uraw
                ubase = p.get("baseline_usdc", {}).get(bot_id, {}).get(chain)
                uusd = None
                if record_pnl and ubase is not None:
                    uusd = round((uraw - ubase) / usdc_scale(chain), 4)
                    p["realized_usd"][bot_id] = p["realized_usd"].get(bot_id, 0.0) + uusd
                    p["baseline_usdc"][bot_id].pop(chain, None)
''',
'''                unsure.pop(chain + ":usdc", None)
                swept[chain + ":usdc"] = uraw
                ubase = p.get("baseline_usdc", {}).get(bot_id, {}).get(chain)
                if ubase is None and bot_id in p.get("baseline", {}):
                    ubase = 0                         # 15k: funded with native only: all swept USDC is profit
                uusd = None
                if record_pnl and ubase is not None:
                    uusd = round((uraw - ubase) / usdc_scale(chain), 4)
                    p["realized_usd"][bot_id] = p["realized_usd"].get(bot_id, 0.0) + uusd
                    p.setdefault("baseline_usdc", {}).setdefault(bot_id, {}).pop(chain, None)
'''),
("settle_usdc_in_flight: the same",
'''        ubase = p.get("baseline_usdc", {}).get(bot_id, {}).get(chain)
        uusd = None
        if record_pnl and ubase is not None:
            uusd = round((fl["usdc"] - ubase) / usdc_scale(chain), 4)
            p["realized_usd"][bot_id] = p["realized_usd"].get(bot_id, 0.0) + uusd
            p["baseline_usdc"][bot_id].pop(chain, None)
''',
'''        ubase = p.get("baseline_usdc", {}).get(bot_id, {}).get(chain)
        if ubase is None and bot_id in p.get("baseline", {}):
            ubase = 0                                 # 15k: funded with native only: all swept USDC is profit
        uusd = None
        if record_pnl and ubase is not None:
            uusd = round((fl["usdc"] - ubase) / usdc_scale(chain), 4)
            p["realized_usd"][bot_id] = p["realized_usd"].get(bot_id, 0.0) + uusd
            p.setdefault("baseline_usdc", {}).setdefault(bot_id, {}).pop(chain, None)
'''),
]

DASH = [
("pnl_history: native and USDC sweep records",
'''                if r.get("op") == "sweep" and r.get("usd") is not None:
''',
'''                if r.get("op") in SWEEP_OPS and isinstance(r.get("usd"), (int, float)):     # 15k: USDC legs too
'''),
("swept_total: native and USDC sweep records",
'''            if isinstance(r, dict) and r.get("op") == "sweep" and isinstance(r.get("usd"), (int, float)):
''',
'''            if isinstance(r, dict) and r.get("op") in SWEEP_OPS and isinstance(r.get("usd"), (int, float)):
'''),
("SWEEP_OPS constant",
'''def pnl_history(days=14):
''',
'''SWEEP_OPS = ("sweep", "sweep_usdc", "sweep_usdc_inflight", "sweep_usdc_fix")   # 15k: gate.log records with a PnL


def pnl_history(days=14):
'''),
]


def patch(text, hunks, name, marker):
    if marker in text:
        print(f"  {name}: already the 15k version")
        return text
    for title, old, new in hunks:
        n = text.count(old)
        if n != 1:
            raise SystemExit(f"{name}: cannot apply '{title}': old text found {n} times (expected 1); nothing was changed")
        text = text.replace(old, new)
        print(f"  {name}: {title}")
    return text


def main(a):
    if len(a) < 3 or a[0] not in ("check", "apply") or (a[0] == "apply" and len(a) < 4):
        raise SystemExit(__doc__)
    g = patch(open(a[1], encoding="utf-8").read(), GATE, "gate-ctl", "# 15k: funded with native only")
    d = patch(open(a[2], encoding="utf-8").read(), DASH, "farm-dash", "# 15k: gate.log records with a PnL")
    if a[0] == "apply":
        os.makedirs(a[3], exist_ok=True)
        for text, base in ((g, "gate-ctl"), (d, "farm-dash")):
            with open(os.path.join(a[3], base), "w", encoding="utf-8") as f:
                f.write(text)
    print(f"patch-15k: {a[0]} ok")


if __name__ == "__main__":
    main(sys.argv[1:])
