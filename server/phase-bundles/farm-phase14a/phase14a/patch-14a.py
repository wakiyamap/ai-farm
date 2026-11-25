#!/usr/bin/env python3
"""Phase 14a text patch of run-role: the builder role gets the claude tool list of the earner role.

  patch-14a.py check <run-role>
  patch-14a.py apply <run-role> <out>
"""
import sys

OLD = "\n    earner)\n"
NEW = "\n    earner|builder)\n"


def main():
    a = sys.argv
    if len(a) < 3 or a[1] not in ("check", "apply"):
        sys.exit(__doc__)
    text = open(a[2], encoding="utf-8").read()
    n = text.count(OLD)
    if n != 1:
        sys.exit(f"{a[2]}: the patch matches {n} times (expected 1); nothing was changed")
    if a[1] == "check":
        print("  run-role: 1 patch matches")
        return
    with open(a[3], "w", encoding="utf-8") as f:
        f.write(text.replace(OLD, NEW))
    print(f"  patched copy written to {a[3]}")


if __name__ == "__main__":
    main()
