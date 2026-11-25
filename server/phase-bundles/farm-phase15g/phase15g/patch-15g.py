#!/usr/bin/env python3
"""Phase 15g text patch of /opt/farm/lib/farmbot_signer.py: an explicit priority fee of 0 stays 0.

  patch-15g.py check <farmbot_signer.py>
  patch-15g.py apply <farmbot_signer.py> <out>

send() chose the tip with `max_priority_fee_per_gas or max_fee_per_gas // 10`, so an explicit 0
(falsy) became maxFee/10 (found by paper-reviewer-claude run 51c32068 on trial-bim-harvest-base;
meta note 2026-11-18-signer-priority-zero.md). Now only a missing value (None) gets the default.
L is unchanged either way: the signer bounds gas x maxFee, not the tip.
"""
import sys

OLD = "max_priority_fee_per_gas or max_fee_per_gas // 10"
NEW = "(max_fee_per_gas // 10 if max_priority_fee_per_gas is None else max_priority_fee_per_gas)"


def main():
    a = sys.argv
    if len(a) < 3 or a[1] not in ("check", "apply"):
        sys.exit(__doc__)
    text = open(a[2], encoding="utf-8").read()
    n = text.count(OLD)
    if n != 1:
        sys.exit(f"{a[2]}: the patch matches {n} times (expected 1); nothing was changed")
    if a[1] == "check":
        return print("  farmbot_signer.py: 1 patch matches")
    with open(a[3], "w", encoding="utf-8") as f:
        f.write(text.replace(OLD, NEW))
    print(f"  patched copy written to {a[3]}")


if __name__ == "__main__":
    main()
