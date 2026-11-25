#!/usr/bin/env python3
"""Phase 10l offline tests (no RPC, no keys, temp dirs only).

  test-10l.py <gate-ctl> <farmchains_dir> [--old]
"""
import contextlib
import hashlib
import importlib.machinery
import importlib.util
import io
import json
import os
import sys
import tempfile
import time

args = [a for a in sys.argv[1:] if a != "--old"]
OLD = "--old" in sys.argv
sys.dont_write_bytecode = True
if len(args) != 2:
    sys.exit(__doc__)
GATE_PATH, FC_DIR = args
sys.path.insert(0, FC_DIR)
STUB = os.environ.get("FARMKEYS_STUB")      # local development only; the server uses /opt/farm/lib
if STUB:
    sys.path.insert(0, STUB)
import farmchains  # noqa: E402

RESULTS = []


def case(name):
    def deco(fn):
        def run():
            real = time.sleep
            time.sleep = lambda s: None
            err = io.StringIO()
            try:
                with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stderr(err), \
                        contextlib.redirect_stdout(io.StringIO()):
                    fn(tmp)
                RESULTS.append((name, True, ""))
            except SystemExit as exc:
                RESULTS.append((name, False, f"exited: {err.getvalue().strip()[-300:] or exc}"))
            except Exception as exc:                       # noqa: BLE001
                RESULTS.append((name, False, f"{type(exc).__name__}: {exc}"))
            finally:
                time.sleep = real
        run.__name__ = "run"
        return run
    return deco


class Chain:
    def __init__(self):
        self.native, self.sends, self.estimate = {}, 0, 400_000

    def call(self, chain, method, params, lane="live"):
        if method == "eth_call":
            if params[0]["to"].lower() == farmchains.ETH_USD_FEED[chain].lower():
                return hex(int(2000 * 1e8))
            return "0x0"
        if method == "eth_getBalance":
            return hex(self.native.get((chain, params[0]), 0))
        if method == "eth_getTransactionCount":
            return hex(0)
        if method == "eth_gasPrice":
            return hex(10**9)
        if method == "eth_estimateGas":
            if isinstance(self.estimate, Exception):
                raise self.estimate
            if "to" in params[0]:                  # a transfer, not the deployment
                return hex(21_000)
            return hex(self.estimate)
        if method == "eth_sendRawTransaction":
            self.sends += 1
            return "0x" + hashlib.sha256(str(self.sends).encode()).hexdigest()
        if method == "eth_getTransactionReceipt":
            return {"status": "0x1"}
        raise AssertionError(method)


def gate(tmp):
    name = f"g{time.time_ns()}"
    loader = importlib.machinery.SourceFileLoader(name, GATE_PATH)
    g_mod = importlib.util.module_from_spec(importlib.util.spec_from_loader(name, loader))
    loader.exec_module(g_mod)
    ws, st = f"{tmp}/ws", f"{tmp}/st"
    for d in (st, f"{ws}/bots/paper", f"{ws}/bots/live", f"{ws}/bots/archive"):
        os.makedirs(d, exist_ok=True)
    g_mod.WS, g_mod.STATE, g_mod.LOG, g_mod.PNL = ws, st, f"{st}/gate.log", f"{st}/pnl.json"
    g_mod.PAPER, g_mod.LIVE, g_mod.ARCHIVE = f"{ws}/bots/paper", f"{ws}/bots/live", f"{ws}/bots/archive"
    chain = Chain()
    g = g_mod.Gate.__new__(g_mod.Gate)
    g.cfg = {"chains": ["ethereum"], "max_capital_usd": 2000, "max_daily_loss_usd": 200, "max_loss_per_tx_usd": 50,
             "max_capital_per_bot_usd": 400, "gas_wallet_cap_usd": {}, "usdc": {}, "relay_url": "x"}
    g.rpc, g._price, g.master = chain, {}, None
    g.key = lambda label, create=False: hashlib.sha256(("farm-test:" + label).encode()).digest()
    g.wait_receipt = lambda *a, **k: {"status": "0x1"}
    calls = []

    class Sub:
        @staticmethod
        def run(a, **kw):
            calls.append(a)
            if "adopt" in a:
                os.rename(f"{g_mod.PAPER}/{a[-1]}", f"{g_mod.LIVE}/{a[-1]}")
                os.makedirs(f"{g_mod.LIVE}/{a[-1]}/state", exist_ok=True)

            class R:
                returncode, stdout, stderr = 0, "", ""
            return R()
    g_mod.subprocess = Sub
    chain.native[("ethereum", g.intermediate())] = int(0.5 * 1e18)
    return g_mod, g, chain, calls


def bot(g_mod, bid, where, art_rel, make_art=True, stale=False):
    d = f"{where}/{bid}"
    os.makedirs(f"{d}/state")
    with open(f"{d}/manifest.yaml", "w") as f:
        f.write(f"id: {bid}\nchains: [ethereum]\nstrategy: t\ncapital_usd: 30\nmax_loss_per_tx_usd: 20\n"
                f"allowed_contracts: []\nexecutor: {art_rel}\n")
    with open(f"{d}/bot.js", "w") as f:
        f.write("const exec = process.env.EXECUTOR_ADDR;\n")
    if make_art:
        p = f"{d}/contracts/out/E.sol/E.json"
        os.makedirs(os.path.dirname(p))
        with open(p, "w") as f:
            json.dump({"bytecode": {"object": "0x6080604052" + "00" * 40}}, f)
    if stale:
        with open(f"{d}/state/executor.json", "w") as f:
            json.dump({"ethereum": {"address": "0x9abb8601e8352db4ee7a3ca35d1898775deee0ef", "txHash": "0x5f", "nonce": 1}}, f)


ART = "bots/paper/{id}/contracts/out/E.sol/E.json"


def refused(g, chain, calls, g_mod, bid):
    try:
        g.promote(bid)
        raise AssertionError("promoted")
    except SystemExit:
        pass
    assert chain.sends == 0 and not any("adopt" in a for a in calls), (chain.sends, calls)
    assert os.path.isdir(f"{g_mod.PAPER}/{bid}") and not os.path.exists(f"{g_mod.LIVE}/{bid}")


@case("promote: an executor that needs 3,190,399 gas on ethereum is refused before the bot is moved or funded")
def t_big(tmp):
    g_mod, g, chain, calls = gate(tmp)
    chain.estimate = 2_658_666                      # x1.2 = 3,190,399 (morpho-watcher2-ethereum)
    bot(g_mod, "big1", g_mod.PAPER, ART.format(id="big1"))
    refused(g, chain, calls, g_mod, "big1")


@case("promote: a deployment that cannot be estimated (reverting constructor) is refused before anything moves")
def t_revert(tmp):
    g_mod, g, chain, calls = gate(tmp)
    chain.estimate = RuntimeError("execution reverted")
    bot(g_mod, "rev1", g_mod.PAPER, ART.format(id="rev1"))
    refused(g, chain, calls, g_mod, "rev1")


@case("promote: an executor just under the limit (2,999,999 gas after the 1.2 margin) still deploys")
def t_edge(tmp):
    g_mod, g, chain, _ = gate(tmp)
    chain.estimate = 2_499_999
    bot(g_mod, "edge1", g_mod.PAPER, ART.format(id="edge1"))
    g.promote("edge1")
    assert g.executor_state_ok("edge1") and chain.sends == 2, chain.sends


@case("promote: a bot without an executor is not estimated and still promotes")
def t_noexec(tmp):
    g_mod, g, chain, _ = gate(tmp)
    chain.estimate = AssertionError("estimated")
    d = f"{g_mod.PAPER}/eoa1"
    os.makedirs(f"{d}/state")
    with open(f"{d}/manifest.yaml", "w") as f:
        f.write("id: eoa1\nchains: [ethereum]\nstrategy: t\ncapital_usd: 30\nmax_loss_per_tx_usd: 20\n"
                "allowed_contracts:\n  - 0x000000000000000000000000000000000000dEaD\n")
    g.promote("eoa1")
    assert chain.sends == 1 and os.path.isdir(f"{g_mod.LIVE}/eoa1"), chain.sends


for fn in list(globals().values()):
    if callable(fn) and getattr(fn, "__name__", "") == "run":
        fn()

print(f"== {'before 10l (installed file)' if OLD else 'phase 10l'}")
for name, ok, why in RESULTS:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"\n        {why}" if why else ""))
failed = [r for r in RESULTS if not r[1]]
if not OLD:
    print("ALL PASS" if not failed else f"{len(failed)} FAILED")
    sys.exit(1 if failed else 0)
