#!/usr/bin/env python3
"""Phase 9k: exact-text patches for the installed gate-ctl and run-role (safe to re-run).

  patch-9k.py check <gate-ctl> <run-role>
  patch-9k.py apply <gate-ctl> <run-role> <outdir>
"""
import os
import sys

GATE = [
("manifest_number(): numeric scalars may carry a trailing comment and YAML quotes",
'''
CONF = "/etc/farm/gate.json"
''',
'''

def manifest_number(line):
    """Number on a top-level `key: value` manifest line. A trailing `# comment` and YAML quotes are
    allowed (9k; `capital_usd: 16 # ...` crashed promote with ValueError before funding)."""
    key, raw = line.split(":", 1)
    raw = raw.split("#", 1)[0].strip().strip("'\\"")
    try:
        return float(raw)
    except ValueError:
        die(f"manifest {key.strip()} must be a number, got {raw!r}")

CONF = "/etc/farm/gate.json"
''',
"def manifest_number(line):"),
("promote: capital_usd / max_loss_per_tx_usd read with manifest_number",
'''            if line.startswith("capital_usd:"):
                cap = float(line.split(":", 1)[1])
            if line.startswith("max_loss_per_tx_usd:"):
                if float(line.split(":", 1)[1]) > self.cfg["max_loss_per_tx_usd"]:
''',
'''            if line.startswith("capital_usd:"):
                cap = manifest_number(line)
            if line.startswith("max_loss_per_tx_usd:"):
                if manifest_number(line) > self.cfg["max_loss_per_tx_usd"]:
''',
"cap = manifest_number(line)"),
("principal_usdc read with manifest_number (quotes too)",
'''                if line.startswith("principal_usdc:"):
                    try:
                        return float(line.split(":", 1)[1].split("#")[0])
                    except ValueError:
                        die("principal_usdc must be a number")
''',
'''                if line.startswith("principal_usdc:"):
                    return manifest_number(line)
''',
'''                if line.startswith("principal_usdc:"):
                    return manifest_number(line)
'''),
]

RUNROLE = [
("researcher (claude harness) may edit prompts/roles/TOOLS.md, as common.md says",
'''      echo "$common,Bash(date*),Bash(python3 *),Bash(jq *),Edit($ws/tools/**),Edit($ws/inbox/**)" ;;
''',
'''      # TOOLS.md lines are the researcher's to add (common.md); only that file under prompts/ (9k)
      echo "$common,Bash(date*),Bash(python3 *),Bash(jq *),Edit($ws/tools/**),Edit($ws/inbox/**),Edit(//srv/farm/prompts/roles/TOOLS.md)" ;;
''',
"Edit(//srv/farm/prompts/roles/TOOLS.md)\" ;;"),
]


def patch(text, hunks, name):
    for title, old, new, marker in hunks:
        if marker in text:
            print(f"  {name}: already applied: {title}")
            continue
        n = text.count(old)
        if n != 1:
            raise SystemExit(f"{name}: cannot apply '{title}': old text found {n} times (expected 1); nothing was changed")
        text = text.replace(old, new)
        print(f"  {name}: applied: {title}")
    return text


def main(argv):
    if len(argv) < 3 or argv[0] not in ("check", "apply"):
        raise SystemExit(__doc__)
    g = patch(open(argv[1], encoding="utf-8").read(), GATE, "gate-ctl")
    r = patch(open(argv[2], encoding="utf-8").read(), RUNROLE, "run-role")
    if argv[0] == "apply":
        os.makedirs(argv[3], exist_ok=True)
        for content, base in ((g, "gate-ctl"), (r, "run-role")):
            with open(os.path.join(argv[3], base), "w", encoding="utf-8") as f:
                f.write(content)
    print(f"patch-9k: {argv[0]} ok")


if __name__ == "__main__":
    main(sys.argv[1:])
