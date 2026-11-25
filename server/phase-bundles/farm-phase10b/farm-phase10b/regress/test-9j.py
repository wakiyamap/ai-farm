#!/usr/bin/env python3
"""Phase 9j offline test: deploy_executor with quoted / unquoted / commented `executor:` paths
against a fake chain in a temp dir (no RPC, no keys, no gate state).

  test-9j.py <gate-ctl> [--old]
"""
import hashlib
import importlib.machinery
import importlib.util
import io
import json
import os
import sys
import tempfile
import contextlib

PATH = sys.argv[1]
OLD = "--old" in sys.argv
if os.environ.get("FARMKEYS_STUB"):
    sys.path.insert(0, os.environ["FARMKEYS_STUB"])


class Chain:
    def call(self, chain, method, params, lane="live"):
        return {"eth_gasPrice": "0x989680", "eth_getTransactionCount": "0x0", "eth_estimateGas": "0x186a0",
                "eth_sendRawTransaction": "0x" + "ab" * 32,
                "eth_getTransactionReceipt": {"status": "0x1"}}[method]


STYLES = {
    "unquoted": 'executor: scratch/mw/out/X.sol/X.json\n',
    "double-quoted": 'executor: "scratch/mw/out/X.sol/X.json"\n',
    "single-quoted": "executor: 'scratch/mw/out/X.sol/X.json'\n",
    "trailing comment": 'executor: "scratch/mw/out/X.sol/X.json"   # forge artifact\n',
}
results = []
for name, line in STYLES.items():
    loader = importlib.machinery.SourceFileLoader(f"g9j_{abs(hash(name))}", PATH)
    m = importlib.util.module_from_spec(importlib.util.spec_from_loader(loader.name, loader))
    loader.exec_module(m)
    with tempfile.TemporaryDirectory() as tmp:
        m.WS, m.LIVE, m.LOG = tmp, f"{tmp}/bots/live", f"{tmp}/gate.log"
        os.makedirs(f"{tmp}/bots/live/mw/state")
        os.makedirs(f"{tmp}/scratch/mw/out/X.sol")
        json.dump({"bytecode": {"object": "0x6080604052"}}, open(f"{tmp}/scratch/mw/out/X.sol/X.json", "w"))
        g = m.Gate.__new__(m.Gate)
        g.cfg, g.rpc, g._price = {}, Chain(), {}
        g.key = lambda label, create=False: hashlib.sha256(label.encode()).digest()
        err = io.StringIO()
        try:
            with contextlib.redirect_stderr(err):
                out = g.deploy_executor("mw", "id: mw\n" + line, ["base"])
            ok = bool(out and out["base"]["address"].startswith("0x")) and os.path.exists(f"{tmp}/bots/live/mw/state/executor.json")
            results.append((name, ok, "" if ok else f"returned {out}"))
        except SystemExit:
            results.append((name, False, err.getvalue().strip()))
        except Exception as exc:
            results.append((name, False, f"{type(exc).__name__}: {exc}"))

print(f"== {'phase 9i (before)' if OLD else 'phase 9j'}: deploy_executor reads the executor path")
for name, ok, why in results:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"\n        {why}" if why else ""))
if not OLD:
    bad = [r for r in results if not r[1]]
    print("ALL PASS" if not bad else f"{len(bad)} FAILED")
    sys.exit(1 if bad else 0)
