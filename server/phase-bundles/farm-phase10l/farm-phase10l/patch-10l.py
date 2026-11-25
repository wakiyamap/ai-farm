#!/usr/bin/env python3
"""Phase 10l: exact-text patch for gate-ctl - promote estimates the executor deployment on every
chain before anything moves (it did so only on hyperevm).

  patch-10l.py check <gate-ctl>
  patch-10l.py apply <gate-ctl> <outdir>

Every old text must occur exactly once, or nothing is written. Safe to re-run (markers).
"""
import os
import sys

GATE = [
("check_deploy_gas: every chain of the bot, not only the small-block ones",
r'''        """On chains that include only small transactions for farm keys (farmchains.max_tx_gas
        below the usual 3M: hyperevm), refuse a promote whose executor deployment would not fit,
        before any funds move (10b)."""
        small = [c for c in chains if max_tx_gas(c) < 3_000_000]
        if not small:
            return
        code = self.executor_code(manifest_text, bot_addr)
        if code is None:
            return
        for chain in small:
            try:
                gas = int(self.rpc.call(chain, "eth_estimateGas", [{"from": bot_addr, "data": code}]), 16)
            except (RuntimeError, ValueError, OSError) as exc:
                die(f"cannot estimate the executor deployment on {chain}: {exc}")
            if int(gas * 1.2) > max_tx_gas(chain):
                die(f"executor deployment on {chain} needs {int(gas * 1.2):,} gas; {chain} includes at most "
                    f"{max_tx_gas(chain):,} per transaction for farm keys (small blocks). Shrink the contract")
''',
r'''        """Refuse a promote whose executor deployment would not fit farmchains.max_tx_gas (or
        cannot be estimated at all, e.g. a reverting constructor) before any funds move. 10b did
        this on hyperevm only; on the other chains deploy_executor refused after the bot had been
        moved to live and funded (10l; 2026-11-11 morpho-watcher2-ethereum, 3,190,399 gas)."""
        code = self.executor_code(manifest_text, bot_addr)
        if code is None:
            return
        for chain in chains:
            try:
                gas = int(self.rpc.call(chain, "eth_estimateGas", [{"from": bot_addr, "data": code}]), 16)
            except (RuntimeError, ValueError, OSError) as exc:
                die(f"cannot estimate the executor deployment on {chain}: {exc}; nothing was moved or funded")
            if int(gas * 1.2) > max_tx_gas(chain):
                die(f"executor deployment on {chain} needs {int(gas * 1.2):,} gas; the gate sends at most "
                    f"{max_tx_gas(chain):,} per transaction on {chain}. Shrink the contract; nothing was moved or funded")
''',
"nothing was moved or funded"),
]


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
    if len(argv) == 2 and argv[0] == "check":
        out = None
    elif len(argv) == 3 and argv[0] == "apply":
        out = argv[2]
    else:
        sys.exit(__doc__)
    with open(argv[1], encoding="utf-8") as f:
        text = patch(f.read(), GATE, "gate-ctl")
    if out:
        with open(os.path.join(out, "gate-ctl"), "w", encoding="utf-8") as f:
            f.write(text)


if __name__ == "__main__":
    main(sys.argv[1:])
