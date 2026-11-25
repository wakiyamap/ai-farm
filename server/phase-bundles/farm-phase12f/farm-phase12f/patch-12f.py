#!/usr/bin/env python3
"""Phase 12f text patches.

  patch-12f.py check <farm.nft>            every old text occurs exactly once
  patch-12f.py apply <farm.nft> <outdir>   write the patched copy into <outdir>
  patch-12f.py tools <TOOLS.md> <out>      add the relayapi row to a copy of TOOLS.md

farm.nft: the earner may reach 127.0.0.1:29485 (farm-relayapi). The bots may not.
TOOLS.md is meta's file, so it is not held to a sha256: the row goes after the `| explorer |`
  row if that row exists exactly once, and nothing is done otherwise.
"""
import sys

NFT = [
    ("""29484 (farm-explorer, earner only). 9013""",
     """29484 (farm-explorer, earner only), 29485 (farm-relayapi, earner only). 9013"""),
    ("""9001-9009, 29483, 29484 } reject with tcp reset
""",
     """9001-9009, 29483, 29484, 29485 } reject with tcp reset
"""),
]

ROW = ("| relayapi | Relay (relay.link) API with the human's key added by a local service: call "
       "`http://127.0.0.1:29485/<path>` instead of `https://api.relay.link/<path>`. Data only (quote, price, chains, "
       "currencies, requests, intents/status); it cannot send | "
       "`curl -s 'http://127.0.0.1:29485/requests/v3?limit=5'` | all |\n")


def patched(path, check_only=False):
    text = open(path, encoding="utf-8").read()
    for i, (old, new) in enumerate(NFT, 1):
        n = text.count(old)
        if n != 1:
            sys.exit(f"{path}: patch {i} matches {n} times (expected 1); nothing was changed")
        if not check_only:
            text = text.replace(old, new)
    return text


def tools(path, out):
    text = open(path, encoding="utf-8").read()
    if "| relayapi |" in text:
        print("  relayapi row: already there")
    else:
        rows = [ln for ln in text.splitlines(keepends=True) if ln.startswith("| explorer |")]
        if len(rows) == 1 and rows[0].endswith("\n"):
            text = text.replace(rows[0], rows[0] + ROW)
            print("  relayapi row: added after the explorer row")
        else:
            print(f"  relayapi row: NOT added (found {len(rows)} `| explorer |` rows); meta adds it from the note")
    with open(out, "w", encoding="utf-8") as f:
        f.write(text)


def main():
    a = sys.argv
    if len(a) == 4 and a[1] == "tools":
        return tools(a[2], a[3])
    if len(a) == 3 and a[1] == "check":
        patched(a[2], True)
        return print(f"  farm.nft: {len(NFT)} patches match")
    if len(a) == 4 and a[1] == "apply":
        with open(f"{a[3]}/farm.nft", "w", encoding="utf-8") as f:
            f.write(patched(a[2]))
        return print(f"  patched copy written to {a[3]}")
    sys.exit(__doc__)


if __name__ == "__main__":
    main()
