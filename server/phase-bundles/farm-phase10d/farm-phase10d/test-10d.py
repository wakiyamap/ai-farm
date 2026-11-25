#!/usr/bin/env python3
"""Phase 10d offline tests (no RPC, no keys, temp dirs only).

  test-10d.py <gate-ctl> <run-role> <common.md> <farmchains_dir> [--old]
"""
import contextlib
import hashlib
import importlib.machinery
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import time

args = [a for a in sys.argv[1:] if a != "--old"]
OLD = "--old" in sys.argv
if len(args) != 4:
    sys.exit(__doc__)
GATE_PATH, RUNROLE_PATH, COMMON_PATH, FC_DIR = args
sys.path.insert(0, FC_DIR)
STUB = os.environ.get("FARMKEYS_STUB")
if STUB:
    sys.path.insert(0, STUB)
import farmchains  # noqa: E402

RESULTS = []


def case(name):
    def deco(fn):
        def run():
            real = time.sleep
            time.sleep = lambda s: None
            try:
                with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stderr(io.StringIO()), \
                        contextlib.redirect_stdout(io.StringIO()):
                    fn(tmp)
                RESULTS.append((name, True, ""))
            except SystemExit as exc:
                RESULTS.append((name, False, f"exited: {exc}"))
            except Exception as exc:                       # noqa: BLE001
                RESULTS.append((name, False, f"{type(exc).__name__}: {exc}"))
            finally:
                time.sleep = real
        run.__name__ = "run"
        return run
    return deco


class Chain:
    def __init__(self):
        self.native, self.sends = {}, 0

    def call(self, chain, method, params, lane="live"):
        if method == "eth_call":
            if params[0]["to"].lower() == farmchains.ETH_USD_FEED[chain].lower():
                return hex(int(2000 * 1e8))
            return "0x0"
        if method == "eth_getBalance":
            return hex(self.native.get((chain, params[0]), 0))
        if method == "eth_getTransactionCount":
            return hex(5 + self.sends)
        if method == "eth_gasPrice":
            return hex(10**9)
        if method == "eth_estimateGas":
            return hex(400_000)
        if method == "eth_sendRawTransaction":
            self.sends += 1
            return "0x" + hashlib.sha256(str(self.sends).encode()).hexdigest()
        if method == "eth_getTransactionReceipt":
            return {"status": "0x1"}
        raise AssertionError(method)


def gate(tmp, manifest, artifact):
    name = f"g{time.time_ns()}"
    loader = importlib.machinery.SourceFileLoader(name, GATE_PATH)
    g_mod = importlib.util.module_from_spec(importlib.util.spec_from_loader(name, loader))
    loader.exec_module(g_mod)
    ws, st = f"{tmp}/ws", f"{tmp}/st"
    for d in (st, f"{ws}/bots/paper/b1", f"{ws}/bots/live", f"{ws}/bots/archive"):
        os.makedirs(d, exist_ok=True)
    g_mod.WS, g_mod.STATE, g_mod.LOG, g_mod.PNL = ws, st, f"{st}/gate.log", f"{st}/pnl.json"
    g_mod.PAPER, g_mod.LIVE, g_mod.ARCHIVE = f"{ws}/bots/paper", f"{ws}/bots/live", f"{ws}/bots/archive"
    open(f"{ws}/bots/paper/b1/manifest.yaml", "w").write(manifest)
    if artifact:
        os.makedirs(f"{ws}/scratch/x", exist_ok=True)
        json.dump({"bytecode": {"object": "0x6080604052" + "00" * 40}}, open(f"{ws}/scratch/x/E.json", "w"))
    chain = Chain()
    g = g_mod.Gate.__new__(g_mod.Gate)
    g.cfg = {"chains": ["ethereum"], "max_capital_usd": 2000, "max_daily_loss_usd": 200, "max_loss_per_tx_usd": 50,
             "max_capital_per_bot_usd": 400, "gas_wallet_cap_usd": {}, "usdc": {}, "relay_url": "x"}
    g.rpc, g._price, g.master = chain, {}, None
    g.key = lambda label, create=False: hashlib.sha256(label.encode()).digest()
    g.wait_receipt = lambda *a, **k: {"status": "0x1"}

    class Sub:
        @staticmethod
        def run(a, **kw):
            if "adopt" in a:
                os.rename(f"{g_mod.PAPER}/b1", f"{g_mod.LIVE}/b1")
                os.makedirs(f"{g_mod.LIVE}/b1/state", exist_ok=True)

            class R:
                returncode, stdout, stderr = 0, "", ""
            return R()
    g_mod.subprocess = Sub
    chain.native[("ethereum", g.intermediate())] = int(0.5 * 1e18)
    return g_mod, g


BASE = "id: b1\nchains: [ethereum]\nstrategy: t\ncapital_usd: 20\nmax_loss_per_tx_usd: 20\n"


@case("gate: an executor bot with an empty allowed_contracts is promoted (executor deployed)")
def t_exec_empty(tmp):
    g_mod, g = gate(tmp, BASE + "allowed_contracts: []\nexecutor: scratch/x/E.json\n", True)
    g.promote("b1")
    assert os.path.exists(f"{g_mod.LIVE}/b1/state/executor.json")


@case("gate: no executor and no allowed_contracts is still refused")
def t_noexec_empty(tmp):
    g_mod, g = gate(tmp, BASE + "allowed_contracts: []\n", False)
    try:
        g.promote("b1")
        raise AssertionError("promoted")
    except SystemExit:
        pass
    assert os.path.isdir(f"{g_mod.PAPER}/b1")


@case("run-role: the live-operator may cp from archive, mkdir in paper, mv inbox/live notes; others may not")
def t_runrole(tmp):
    src = open(RUNROLE_PATH).read()
    i = src.index("claude_tools() {")
    j = src.index("\n}\n", i) + 3
    fn = src[i:j]
    def tools(role):
        return subprocess.run(["bash", "-c", fn + "\nROLE=" + role + "\nclaude_tools"], capture_output=True,
                              text=True, check=True).stdout
    lo = tools("live-operator")
    for r in ("Bash(cp -r /srv/farm/ws/bots/archive/*)", "Bash(mkdir -p /srv/farm/ws/bots/paper/*)",
              "Bash(mv /srv/farm/ws/inbox/live/*)"):
        assert r in lo, r
    assert "bots/archive/*" not in tools("paper-reviewer") and "inbox/live/*" not in tools("meta")


@case("common.md: only native and USDC count; allowed_contracts may be empty for an executor bot")
def t_common(tmp):
    t = open(COMMON_PATH).read()
    assert "Only the native token and the configured USDC count as funds" in t
    assert "may leave it empty" in t


for fn in list(globals().values()):
    if callable(fn) and getattr(fn, "__name__", "") == "run":
        fn()

print(f"== {'before 10d (installed files)' if OLD else 'phase 10d'}")
for name, ok, why in RESULTS:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"\n        {why}" if why else ""))
failed = [r for r in RESULTS if not r[1]]
if not OLD:
    print("ALL PASS" if not failed else f"{len(failed)} FAILED")
    sys.exit(1 if failed else 0)
