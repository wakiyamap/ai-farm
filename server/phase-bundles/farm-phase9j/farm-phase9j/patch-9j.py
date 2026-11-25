#!/usr/bin/env python3
"""Phase 9j: gate-ctl reads a quoted `executor:` path (exact-text patch, safe to re-run).

  patch-9j.py check <gate-ctl>
  patch-9j.py apply <gate-ctl> <outdir>
"""
import os
import sys

OLD = '''        m = re.search(r"^executor:\\s*(\\S+)", manifest_text, re.M)
'''
NEW = '''        # the path may be quoted (YAML string) and may carry a trailing comment (9j)
        m = re.search(r"^executor:\\s*['\\"]?([^'\\"\\s#]+)", manifest_text, re.M)
'''
MARKER = "the path may be quoted (YAML string) and may carry a trailing comment (9j)"


def main(argv):
    if len(argv) < 2 or argv[0] not in ("check", "apply"):
        raise SystemExit(__doc__)
    text = open(argv[1], encoding="utf-8").read()
    if MARKER in text:
        print("  gate-ctl: already applied: quoted executor path")
    else:
        n = text.count(OLD)
        if n != 1:
            raise SystemExit(f"gate-ctl: executor regex found {n} times (expected 1); nothing was changed")
        text = text.replace(OLD, NEW)
        print("  gate-ctl: applied: quoted executor path")
    if argv[0] == "apply":
        os.makedirs(argv[2], exist_ok=True)
        with open(os.path.join(argv[2], "gate-ctl"), "w", encoding="utf-8") as f:
            f.write(text)
    print(f"patch-9j: {argv[0]} ok")


if __name__ == "__main__":
    main(sys.argv[1:])
