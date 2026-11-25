#!/usr/bin/env python3
"""The tip expression of phase 15g, evaluated on its own (the module needs the signer socket)."""
import sys
sys.path.insert(0, sys.argv[1]) if len(sys.argv) > 1 else None
from importlib import util
spec = util.spec_from_file_location("p15g", __file__.replace("test-15g.py", "patch-15g.py"))
p = util.module_from_spec(spec); spec.loader.exec_module(p)
ok = 0
for given, fee, want in ((0, 1000, 0), (None, 1000, 100), (7, 1000, 7)):
    got = eval(p.NEW, {"max_priority_fee_per_gas": given, "max_fee_per_gas": fee})
    old = eval(p.OLD, {"max_priority_fee_per_gas": given, "max_fee_per_gas": fee})
    print(f"  tip given {given!s:>4}, maxFee {fee}: old {old:>4}  new {got:>4}  {'ok' if got == want else 'FAIL'}")
    ok += got == want
print(f"{ok}/3 passed")
sys.exit(0 if ok == 3 else 1)
