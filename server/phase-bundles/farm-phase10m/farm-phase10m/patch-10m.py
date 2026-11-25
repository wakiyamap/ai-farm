#!/usr/bin/env python3
"""Phase 10m: exact-text patch for /srv/farm/prompts/common.md (decision 2026-11-12, items 2 and 5).

  patch-10m.py check <common.md>
  patch-10m.py apply <common.md> <outdir>

Every old text must occur exactly once, or nothing is written. Safe to re-run (markers).
"""
import os
import sys

HUNKS = [
("Workspace table: inbox/live is read only when the watchdog wakes the live-operator",
"| `inbox/live/` | Messages to the live-operator | all |\n",
"| `inbox/live/` | Messages to the live-operator (read only when the watchdog wakes it; non-urgent reports go to `inbox/meta/`) | all |\n",
"read only when the watchdog wakes it"),

("Principle 2: what counts as a latency race",
"If something needs speed we don't have, record it as `blocked_infra` and stop.\n",
"If something needs speed we don't have, record it as `blocked_infra` and stop. Something taken in the "
"price-update block, or within seconds to 1-2 blocks of becoming eligible, counts as a latency race "
"(decision 2026-11-12).\n",
"counts as a latency race"),
]


def patch(text):
    for title, old, new, marker in HUNKS:
        if marker in text:
            print(f"  common.md: already applied: {title}")
            continue
        n = text.count(old)
        if n != 1:
            raise SystemExit(f"common.md: cannot apply '{title}': old text found {n} times (expected 1); "
                             "nothing was changed")
        text = text.replace(old, new)
        print(f"  common.md: applied: {title}")
    return text


def main(argv):
    if len(argv) == 2 and argv[0] == "check":
        out = None
    elif len(argv) == 3 and argv[0] == "apply":
        out = argv[2]
    else:
        sys.exit(__doc__)
    with open(argv[1], encoding="utf-8") as f:
        text = patch(f.read())
    if out:
        with open(os.path.join(out, "common.md"), "w", encoding="utf-8") as f:
            f.write(text)


if __name__ == "__main__":
    main(sys.argv[1:])
