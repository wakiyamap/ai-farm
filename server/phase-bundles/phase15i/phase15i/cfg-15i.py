#!/usr/bin/env python3
"""Phase 15i config changes (decision 2026-11-20: use the Alchemy month up to 11-24).

  cfg-15i.py check <relay.json> <feed.json>
  cfg-15i.py apply <relay.json> <feed.json> <outdir>

relay.json alchemy_daily_cu:
  fork      600,000 -> 95,200,000  (the relay no longer looks at it for fork reads - 15i sends every fork
                                    read to Alchemy - but /health and the dashboard show it, so it is set
                                    to the month so no agent reports "fork budget spent")
  research  700,000 -> 1,500,000
  scout     300,000 -> 1,200,000
feed.json max_log_filters_per_chain 8 -> 16 (base was full: new bots polled instead).
A key that already has the new value is left alone; any other value stops the script.
"""
import json
import os
import sys

RELAY = {"fork": (600000, 95200000), "research": (700000, 1500000), "scout": (300000, 1200000)}
FEED = {"max_log_filters_per_chain": (8, 16)}


def change(d, wanted, name):
    for k, (old, new) in wanted.items():
        v = d.get(k)
        if v == new:
            print(f"  {name}: {k} already {new:,}")
        elif v == old:
            d[k] = new
            print(f"  {name}: {k} {old:,} -> {new:,}")
        else:
            raise SystemExit(f"{name}: {k} is {v!r}, expected {old} (or {new}); nothing was changed")


def main(a):
    if len(a) < 3 or a[0] not in ("check", "apply") or (a[0] == "apply" and len(a) < 4):
        raise SystemExit(__doc__)
    relay = json.load(open(a[1], encoding="utf-8"))
    feed = json.load(open(a[2], encoding="utf-8"))
    change(relay["alchemy_daily_cu"], RELAY, "relay.json")
    change(feed, FEED, "feed.json")
    if a[0] == "apply":
        os.makedirs(a[3], exist_ok=True)
        for obj, base in ((relay, "relay.json"), (feed, "feed.json")):
            with open(os.path.join(a[3], base), "w", encoding="utf-8") as f:
                json.dump(obj, f, indent=2)
                f.write("\n")
    print(f"cfg-15i: {a[0]} ok")


if __name__ == "__main__":
    main(sys.argv[1:])
