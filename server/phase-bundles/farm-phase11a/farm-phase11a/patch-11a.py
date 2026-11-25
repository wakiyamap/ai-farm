#!/usr/bin/env python3
"""Phase 11a: exact-text patches for /etc/farm/farm.nft and /srv/farm/prompts/common.md.

  patch-11a.py check <farm.nft> <common.md>
  patch-11a.py apply <farm.nft> <common.md> <outdir>

Every old text must occur exactly the expected number of times, or nothing is written.
Safe to re-run (markers).
"""
import os
import sys

HUNKS = {
"farm.nft": [
("the earner and the bots may reach the feed on 8546",
 "8545, 9001-9009", "8545, 8546, 9001-9009", "8545, 8546, 9001-9009", 2),
],
"common.md": [
("Principle 2: same block is a latency race; one block later may be tried through the feed; two or more count",
 " Something taken in the price-update block, or within seconds to 1-2 blocks of becoming eligible, "
 "counts as a latency race (decision 2026-11-12).\n",
 " Something taken in the same block as its trigger (price update, auction start) is a latency race: out "
 "of scope. Something taken one block later may be attempted by a bot that waits on the feed "
 "(`http://127.0.0.1:8546`, wiki `infra/feed.md`) but does not count as expected revenue; two blocks or "
 "more counts (decision 2026-11-13).\n",
 "decision 2026-11-13).", 1),
],
}


def patch(name, text):
    for title, old, new, marker, times in HUNKS[name]:
        if marker in text:
            print(f"  {name}: already applied: {title}")
            continue
        n = text.count(old)
        if n != times:
            raise SystemExit(f"{name}: cannot apply '{title}': old text found {n} times (expected {times}); "
                             "nothing was changed")
        text = text.replace(old, new)
        print(f"  {name}: applied: {title}")
    return text


def main(argv):
    if len(argv) == 3 and argv[0] == "check":
        out = None
    elif len(argv) == 4 and argv[0] == "apply":
        out = argv[3]
    else:
        sys.exit(__doc__)
    done = {}
    for name, path in zip(("farm.nft", "common.md"), argv[1:3]):
        with open(path, encoding="utf-8") as f:
            done[name] = patch(name, f.read())
    if out:
        for name, text in done.items():
            with open(os.path.join(out, name), "w", encoding="utf-8") as f:
                f.write(text)


if __name__ == "__main__":
    main(sys.argv[1:])
