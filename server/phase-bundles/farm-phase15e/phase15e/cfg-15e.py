#!/usr/bin/env python3
"""Phase 15e: relay.json budgets.

  cfg-15e.py show  <relay.json>
  cfg-15e.py apply <relay.json> <out.json>

alchemy_daily_cu.watch = 300000 (kept if set); .fork 400000 -> 600000 (only if it is still the 15c
value: on 11-18 the forks used 82k by 03:35 UTC, a pace of about 545k a day). Nothing else changes.
"""
import json
import sys


def show(c):
    print(f"  alchemy_daily_cu {json.dumps(c.get('alchemy_daily_cu', {}))}")


def main():
    a = sys.argv
    if len(a) < 3 or a[1] not in ("show", "apply"):
        sys.exit(__doc__)
    c = json.load(open(a[2], encoding="utf-8"))
    if a[1] == "show":
        return show(c)
    b = c.setdefault("alchemy_daily_cu", {})
    b.setdefault("watch", 300_000)
    if b.get("fork") == 400_000:
        b["fork"] = 600_000
    with open(a[3], "w", encoding="utf-8") as f:
        json.dump(c, f, indent=2)
        f.write("\n")
    show(c)


if __name__ == "__main__":
    main()
