#!/usr/bin/env python3
"""Phase 15f: a second public bsc node in relay.json.

  cfg-15f.py show  <relay.json>
  cfg-15f.py apply <relay.json> <out.json>

Puts https://bsc-dataseed.binance.org first in chains.bsc.public (it answers eth_getLogs, scout
run 9d4669bb measured 20k-block pages; bsc-dataseed.bnbchain.org does not serve eth_getLogs) and
keeps the existing entries after it. Nothing else changes. Idempotent.
"""
import json
import sys

URL = "https://bsc-dataseed.binance.org"


def main():
    a = sys.argv
    if len(a) < 3 or a[1] not in ("show", "apply"):
        sys.exit(__doc__)
    c = json.load(open(a[2], encoding="utf-8"))
    bsc = c.get("chains", {}).get("bsc")
    if not isinstance(bsc, dict) or not isinstance(bsc.get("public"), list):
        sys.exit("relay.json has no chains.bsc.public list; nothing was changed")
    if a[1] == "show":
        return print(f"  chains.bsc.public {json.dumps(bsc['public'])}")
    bsc["public"] = [URL] + [u for u in bsc["public"] if u.rstrip("/") != URL]
    with open(a[3], "w", encoding="utf-8") as f:
        json.dump(c, f, indent=2)
        f.write("\n")
    print(f"  chains.bsc.public {json.dumps(bsc['public'])}")


if __name__ == "__main__":
    main()
