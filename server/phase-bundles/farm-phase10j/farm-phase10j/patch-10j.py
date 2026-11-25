#!/usr/bin/env python3
"""Phase 10j: exact-text patch for the fork CLI.

  patch-10j.py check <fork>
  patch-10j.py apply <fork> <outdir>

Every old text must occur exactly once, or nothing is written. Safe to re-run (markers).
"""
import os
import sys

FORK = [
("chains whose relay-fetched head header has no blob fields",
'''UPSTREAM = {"ethereum-review": "ethereum"}       # fork name -> mainnet chain it mirrors (default: same name)
''',
'''UPSTREAM = {"ethereum-review": "ethereum"}       # fork name -> mainnet chain it mirrors (default: same name)
# 10j: elysium (Arbitrum Orbit) headers carry no excessBlobGas, and anvil then refuses eth_call on
# the freshly forked head with "Excess blob gas not set." One locally mined block has the field.
MINE_AFTER_RESET = {"elysium"}
''',
"MINE_AFTER_RESET = {"),

("reset mines one empty block on those chains",
'''    rpc(url(chain), "anvil_reset", [{"forking": f}])
    g = bump_generation(chain)
''',
'''    rpc(url(chain), "anvil_reset", [{"forking": f}])
    if chain in MINE_AFTER_RESET:
        try:                                         # best effort: the reset itself has succeeded
            out = rpc_raw(url(chain), "evm_mine", [])
            if "error" in out:
                raise RuntimeError(out["error"].get("message"))
            print(f"fork: mined one empty block on {chain} (its forked head has no blob fields); "
                  "the fork is one block past the block you asked for", file=sys.stderr)
        except Exception as exc:                     # noqa: BLE001
            print(f"fork: warning: could not mine a block on {chain} after the reset ({exc}); if eth_call says "
                  "'Excess blob gas not set.', send any transaction on the fork first", file=sys.stderr)
    g = bump_generation(chain)
''',
"if chain in MINE_AFTER_RESET:"),
]


def plan(text, hunks):
    lines = []
    for title, old, new, marker in hunks:
        if marker in text:
            lines.append(f"  already applied: {title}")
            continue
        n = text.count(old)
        if n != 1:
            raise ValueError(f"{title}: the expected text occurs {n} times (must be exactly 1); nothing was changed")
        text = text.replace(old, new)
        lines.append(f"  ok: {title}")
    return text, lines


def main(argv):
    if len(argv) < 2 or argv[0] not in ("check", "apply") or (argv[0] == "apply" and len(argv) != 3):
        sys.exit(__doc__)
    with open(argv[1], encoding="utf-8") as f:
        text = f.read()
    try:
        out, lines = plan(text, FORK)
    except ValueError as exc:
        sys.exit(f"patch-10j: {os.path.basename(argv[1])}: {exc}")
    print(f"{os.path.basename(argv[1])}:")
    print("\n".join(lines))
    if argv[0] == "apply":
        with open(os.path.join(argv[2], os.path.basename(argv[1])), "w", encoding="utf-8") as f:
            f.write(out)


if __name__ == "__main__":
    main(sys.argv[1:])
