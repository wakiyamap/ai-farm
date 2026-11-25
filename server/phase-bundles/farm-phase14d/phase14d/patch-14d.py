#!/usr/bin/env python3
"""Phase 14d text patch of run-role: read tools for the claude-harness paper-reviewer and meta.

  patch-14d.py check <run-role>
  patch-14d.py apply <run-role> <out>

paper-reviewer-claude had `python3 /srv/farm/ws/tools/manifest-check.py` refused (a required review
step); meta had `ls` and `python3 -c` refused. The codex reviewer is not affected (codex ignores this list).
"""
import sys

READ = "Bash(date*),Bash(python3 *),Bash(jq *),Bash(ls *),Bash(cat *),Bash(head *),Bash(tail *),Bash(grep *),Bash(wc *),"
PAIRS = [
    ('echo "$common,Bash(gate promote *),Bash(gate accounts),Bash(gate intermediate),Bash(paper archive *),Edit(',
     'echo "$common,' + READ + 'Bash(gate promote *),Bash(gate accounts),Bash(gate intermediate),Bash(paper archive *),Edit('),
    ('echo "$common,Bash(date*),Edit($ws/**),Edit(//srv/farm/prompts/roles/**),',
     'echo "$common,' + READ + 'Edit($ws/**),Edit(//srv/farm/prompts/roles/**),'),
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
        print(f"  run-role: {len(PAIRS)} patches match")
        return
    with open(a[3], "w", encoding="utf-8") as f:
        f.write(text)
    print(f"  patched copy written to {a[3]}")


if __name__ == "__main__":
    main()
