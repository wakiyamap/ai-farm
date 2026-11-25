#!/usr/bin/env python3
"""Phase 10d: exact-text patches - executor bots may leave allowed_contracts empty (gate-ctl),
the live-operator can send a bot back (run-role), common.md states what counts as funds.

  patch-10d.py check <gate-ctl> <run-role> <common.md>
  patch-10d.py apply <gate-ctl> <run-role> <common.md> <outdir>

Every old text must occur exactly once, or nothing is written. Safe to re-run (markers).
"""
import os
import sys

GATE = [
("promote: allowed_contracts may be empty when the manifest names an executor",
'''        if not allowed:
            die("manifest.yaml must list allowed_contracts (the contracts the bot may call)")
''',
'''        # an executor bot needs no allowed_contracts: the gate deploys the executor and the signer
        # allows that address from state/executor.json. Listing the protocols the executor calls
        # internally would only let the bot wallet call them directly (10d).
        if not allowed and not re.search(r"^executor:\\s*\\S", text, re.M):
            die("manifest.yaml must list allowed_contracts (the contracts the bot wallet sends to) "
                "or name an executor")
''',
"an executor bot needs no allowed_contracts"),
]

RUNROLE = [
("live-operator: copy a stopped bot from archive to paper, file inbox/live notes under done/",
'''      echo "$common,Bash(gate *),Bash(paper *),Edit($ws/inbox/**),Edit($ws/logs/**),Edit($ws/bots/paper/**)" ;;
''',
'''      # sent-back copies (common.md): archive -> paper; handled inbox/live notes -> inbox/live/done (10d)
      echo "$common,Bash(gate *),Bash(paper *),Edit($ws/inbox/**),Edit($ws/logs/**),Edit($ws/bots/paper/**),Bash(cp -r $wsb/bots/archive/*),Bash(cp $wsb/bots/archive/*),Bash(mkdir -p $wsb/bots/paper/*),Bash(mv $wsb/inbox/live/*)" ;;
''',
"handled inbox/live notes -> inbox/live/done (10d)"),
]

COMMON = [
("X: only native and USDC count; allowed_contracts is the wallet's direct targets",
'''and USDC sent out counts toward the daily `capital_usd` spend.''',
'''and USDC sent out counts toward the daily `capital_usd` spend.
  Only the native token and the configured USDC count as funds: X, the sweep at stop and the watchdog's live-loss stop see nothing else. An executor must return profit to the bot wallet as native or USDC; a profit left as another token (ETH+, WETH, an LP share...) is not swept back and counts as lost. `allowed_contracts` lists only what the bot wallet itself sends transactions to. A bot that acts through its executor may leave it empty (the gate deploys the executor and the signer allows it); never list the protocols the executor calls internally, nor a fork-only address.''',
"Only the native token and the configured USDC count as funds"),
]

FILES = [("gate-ctl", GATE), ("run-role", RUNROLE), ("common.md", COMMON)]


def patch(text, hunks, name):
    for title, old, new, marker in hunks:
        if marker in text:
            print(f"  {name}: already applied: {title}")
            continue
        n = text.count(old)
        if n != 1:
            raise SystemExit(f"{name}: cannot apply '{title}': old text found {n} times (expected 1); "
                             "nothing was changed")
        text = text.replace(old, new)
        print(f"  {name}: applied: {title}")
    return text


def main(argv):
    if len(argv) == 4 and argv[0] == "check":
        out = None
    elif len(argv) == 5 and argv[0] == "apply":
        out = argv[4]
    else:
        sys.exit(__doc__)
    results = []
    for path, (name, hunks) in zip(argv[1:4], FILES):
        with open(path, encoding="utf-8") as f:
            results.append((name, patch(f.read(), hunks, name)))
    if out:
        for name, text in results:
            with open(os.path.join(out, name), "w", encoding="utf-8") as f:
                f.write(text)


if __name__ == "__main__":
    main(sys.argv[1:])
