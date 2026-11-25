#!/usr/bin/env python3
"""Phase 15c: relay.json for the fork and scout lanes.

  cfg-15c.py show  <relay.json>              the values this phase sets, as they are now
  cfg-15c.py apply <relay.json> <out.json>   write the new file to <out.json>

Sets alchemy_daily_cu.research = 700000 (was 1,000,000; the scouts move to their own lane),
.fork = 400000, .scout = 300000 (kept if already set), lane_by_user = {"farmfork": "fork",
"earner": "scout"} (merged), alchemy_monthly_cu = 95200000 (kept if set). Nothing else changes.
"""
import json
import sys

RESEARCH = 700_000
DEFAULTS = {"fork": 400_000, "scout": 300_000}
USERS = {"farmfork": "fork", "earner": "scout"}


def show(c):
    b = c.get("alchemy_daily_cu", {})
    print(f"  alchemy_daily_cu {json.dumps(b)}")
    print(f"  lane_by_user {json.dumps(c.get('lane_by_user'))}  alchemy_monthly_cu {c.get('alchemy_monthly_cu')}")


def main():
    a = sys.argv
    if len(a) < 3 or a[1] not in ("show", "apply"):
        sys.exit(__doc__)
    c = json.load(open(a[2], encoding="utf-8"))
    if a[1] == "show":
        return show(c)
    b = c.setdefault("alchemy_daily_cu", {})
    b["research"] = RESEARCH
    for k, v in DEFAULTS.items():
        b.setdefault(k, v)
    u = c.setdefault("lane_by_user", {})
    for k, v in USERS.items():
        u.setdefault(k, v)
    c.setdefault("alchemy_monthly_cu", 95_200_000)
    with open(a[3], "w", encoding="utf-8") as f:
        json.dump(c, f, indent=2)
        f.write("\n")
    show(c)


if __name__ == "__main__":
    main()
