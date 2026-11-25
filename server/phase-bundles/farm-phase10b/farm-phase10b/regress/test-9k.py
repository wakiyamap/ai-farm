#!/usr/bin/env python3
"""Phase 9k offline tests (temp dir, fake chain, no RPC / keys / gate state).

  test-9k.py <gate-ctl> <run-role> [--old]

gate promote must read `capital_usd: 16   # comment`, quoted numbers and principal_usdc the same
way, refuse a non-number cleanly before anything moves, and the researcher's claude permission
set must include Edit on prompts/roles/TOOLS.md (and nothing else under prompts/).
"""
import contextlib
import hashlib
import importlib.machinery
import importlib.util
import io
import os
import subprocess
import sys
import tempfile

GATE, RUNROLE = sys.argv[1], sys.argv[2]
OLD = "--old" in sys.argv
if os.environ.get("FARMKEYS_STUB"):
    sys.path.insert(0, os.environ["FARMKEYS_STUB"])
PRICE = 2132.0


class Reached(Exception):
    pass


class Chain:
    def __init__(self, fk, feeds):
        self.fk, self.feeds, self.native = fk, feeds, {}

    def call(self, chain, method, params, lane="live"):
        if method == "eth_call":
            if params[0]["to"] == self.feeds.get(chain):
                return hex(int(PRICE * 1e8))
            return "0x0"
        if method == "eth_getBalance":
            return hex(self.native.get((chain, params[0]), 0))
        raise AssertionError(method)


def promote_with(manifest):
    loader = importlib.machinery.SourceFileLoader(f"g9k_{abs(hash(manifest))}", GATE)
    m = importlib.util.module_from_spec(importlib.util.spec_from_loader(loader.name, loader))
    loader.exec_module(m)
    with tempfile.TemporaryDirectory() as tmp:
        m.WS, m.STATE = tmp, tmp
        m.PAPER, m.LIVE = f"{tmp}/paper", f"{tmp}/live"
        m.LOG, m.PNL = f"{tmp}/gate.log", f"{tmp}/pnl.json"
        os.makedirs(f"{tmp}/paper/mb")
        os.makedirs(f"{tmp}/live")
        open(f"{tmp}/paper/mb/manifest.yaml", "w").write(manifest)
        g = m.Gate.__new__(m.Gate)
        g.cfg = {"chains": ["ethereum"], "max_capital_usd": 2000, "max_daily_loss_usd": 200, "max_loss_per_tx_usd": 50,
                 "max_capital_per_bot_usd": 400, "usdc": {"ethereum": "0x" + "a0" * 20}, "relay_url": "x"}
        g.rpc, g._price = Chain(m.farmkeys, m.ETH_USD_FEED), {}
        g.key = lambda label, create=False: hashlib.sha256(label.encode()).digest()
        g.usdc_raw = lambda chain, addr: 200 * 10**6      # 200 USDC on the intermediate wallet
        g.rpc.native[("ethereum", g.intermediate())] = int(500 / PRICE * 1e18)

        class Sub:
            @staticmethod
            def run(args, **kw):
                if "adopt" in args:
                    raise Reached()
        m.subprocess = Sub
        err = io.StringIO()
        try:
            with contextlib.redirect_stderr(err):
                g.promote("mb")
        except Reached:
            return "reached adopt", ""
        except SystemExit:
            return "refused", err.getvalue().strip()
        except Exception as exc:
            return "crashed", f"{type(exc).__name__}: {exc}"
    return "returned", ""


BASE = "id: mb\nchains: [ethereum]\nallowed_contracts:\n  - 0x1111111111111111111111111111111111111111\n"
CASES = [
    ("capital_usd with a trailing comment (morpho 11-10)", BASE + "capital_usd: 16   # Fixed gas float\nmax_loss_per_tx_usd: 20\n", "reached adopt", None),
    ("max_loss_per_tx_usd with a trailing comment", BASE + "capital_usd: 16\nmax_loss_per_tx_usd: 20  # worst case\n", "reached adopt", None),
    ("quoted numbers", BASE + "capital_usd: '16'\nmax_loss_per_tx_usd: \"20\"\nprincipal_usdc: '0'\n", "reached adopt", None),
    ("principal_usdc with a comment", BASE + "capital_usd: 120\nprincipal_usdc: 100   # flash-free\nmax_loss_per_tx_usd: 20\n", "reached adopt", None),
    ("max_loss above L is still refused", BASE + "capital_usd: 16\nmax_loss_per_tx_usd: 60 # too high\n", "refused", "exceeds L"),
    ("a non-number is refused cleanly, before anything moves", BASE + "capital_usd: sixteen\nmax_loss_per_tx_usd: 20\n", "refused", "must be a number"),
]
results = []
for name, manifest, want, msg in CASES:
    got, detail = promote_with(manifest)
    ok = got == want and (msg is None or msg in detail)
    results.append((name, ok, "" if ok else f"{got}: {detail}"))

env = dict(os.environ, ROLE="researcher")
tools = subprocess.run(["bash", "-c", f'source <(sed -n "/^claude_tools()/,/^}}/p" "{RUNROLE}"); claude_tools'],
                       capture_output=True, text=True, env=env).stdout.strip().split(",")
prompts = [t for t in tools if "/srv/farm/prompts" in t]
ok = prompts == ["Edit(//srv/farm/prompts/roles/TOOLS.md)"]
results.append(("researcher may Edit prompts/roles/TOOLS.md and nothing else under prompts/", ok, "" if ok else f"got {prompts}"))
meta = subprocess.run(["bash", "-c", f'source <(sed -n "/^claude_tools()/,/^}}/p" "{RUNROLE}"); claude_tools'],
                      capture_output=True, text=True, env=dict(os.environ, ROLE="meta")).stdout
ok = "Edit(//srv/farm/prompts/roles/**)" in meta
results.append(("meta's permission set is unchanged", ok, "" if ok else meta[:200]))

print(f"== {'before 9k' if OLD else 'phase 9k'}: gate-ctl numeric manifest fields / researcher TOOLS.md")
for name, ok, why in results:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"\n        {why}" if why else ""))
if not OLD:
    bad = [r for r in results if not r[1]]
    print("ALL PASS" if not bad else f"{len(bad)} FAILED")
    sys.exit(1 if bad else 0)
