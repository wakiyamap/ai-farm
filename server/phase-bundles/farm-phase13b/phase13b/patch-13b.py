#!/usr/bin/env python3
"""Phase 13b text patch: widen the claude-harness earner's Bash list (run-role).

  patch-13b.py check <run-role>
  patch-13b.py apply <run-role> <out>

The first earner-claude session (run 3fa7205c, 2026-11-16 16:54Z) had two Bash calls refused:
a relative `mkdir -p scratch/...` and a pipeline using `sed`. The refused mkdir then made two
`curl -o` calls fail with exit code 23 (no such directory). mkdir is now allowed for any path
(the OS user decides where it works), and the usual text filters are added.
"""
import sys

OLD = "Bash(sleep *),Bash(cp *),Bash(mkdir -p $wsb/scratch/*),Bash(mkdir -p $wsb/bots/paper/*),"
NEW = ("Bash(sleep *),Bash(cp *),Bash(mkdir *),Bash(cd *),Bash(sed *),Bash(awk *),Bash(sort *),Bash(uniq *),"
       "Bash(cut *),Bash(tr *),Bash(echo *),Bash(printf *),Bash(find *),Bash(diff *),Bash(tee *),")


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
