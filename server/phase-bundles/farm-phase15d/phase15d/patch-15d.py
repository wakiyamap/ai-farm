#!/usr/bin/env python3
"""Phase 15d text patch of farm.nft: earner and farmbot may reach 29486 (farm-hermes, phase 15c).

  patch-15d.py check <farm.nft>
  patch-15d.py apply <farm.nft> <out>
"""
import sys

PAIRS = [
    ("29485 (farm-relayapi, earner only). 9013",
     "29485 (farm-relayapi, earner only), 29486 (farm-hermes, earner and bots). 9013"),
    ("9001-9009, 29483, 29484, 29485 } reject with tcp reset\n",
     "9001-9009, 29483, 29484, 29485, 29486 } reject with tcp reset\n"),
    ("tcp dport != { 53, 8545, 8546, 9001-9009 } reject with tcp reset\n",
     "tcp dport != { 53, 8545, 8546, 9001-9009, 29486 } reject with tcp reset\n"),
]


def main():
    a = sys.argv
    if len(a) < 3 or a[1] not in ("check", "apply"):
        sys.exit(__doc__)
    text = open(a[2], encoding="utf-8").read()
    for i, (old, new) in enumerate(PAIRS, 1):
        n = text.count(old)
        if n != 1:
            sys.exit(f"{a[2]}: patch {i} matches {n} times (expected 1); nothing was changed")
        text = text.replace(old, new)
    if a[1] == "check":
        return print(f"  farm.nft: {len(PAIRS)} patches match")
    with open(a[3], "w", encoding="utf-8") as f:
        f.write(text)
    print(f"  patched copy written to {a[3]}")


if __name__ == "__main__":
    main()
