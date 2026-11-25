#!/usr/bin/env python3
"""Phase 9i offline tests: no RPC, no keys, no files outside a temp directory.

  test-9i.py <gate-ctl> <farm-watchdog> [--old]

Loads the given files as modules and drives Gate.promote / Gate.sweep / Gate.stop_all and the
watchdog's chain parser against a fake chain. With --old the results are only reported (used to
show what the phase 9g files did); otherwise any failure exits 1.
"""
import hashlib
import importlib.machinery
import importlib.util
import io
import json
import os
import sys
import tempfile
import time
import contextlib

GATE_PATH, WD_PATH = sys.argv[1], sys.argv[2]
OLD = "--old" in sys.argv
STUB = os.environ.get("FARMKEYS_STUB")      # local development only; the server uses /opt/farm/lib
if STUB:
    sys.path.insert(0, STUB)


def load(path, name):
    loader = importlib.machinery.SourceFileLoader(name, path)
    mod = importlib.util.module_from_spec(importlib.util.spec_from_loader(name, loader))
    loader.exec_module(mod)
    return mod


class Reached(Exception):
    pass


class FakeClock:
    """time.monotonic / time.sleep without waiting (poll_receipt waits up to 180 s)."""
    def __init__(self):
        self.t = 0.0

    def monotonic(self):
        return self.t

    def sleep(self, s):
        self.t += s


PRICE = 2132.0
USDC_BASE = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"


class FakeChain:
    def __init__(self, fk, feeds, usdc):
        self.fk, self.feeds, self.usdc = fk, feeds, usdc
        self.native = {}      # (chain, addr) -> wei
        self.erc20 = {}       # (chain, addr) -> raw
        self.sends = {}       # chain -> count
        self.receipt_mode = "ok"   # ok | none | revert
        self.sent = []        # (chain, hash)

    def usd_wei(self, usd):
        return int(usd / PRICE * 1e18)

    def call(self, chain, method, params, lane="live"):
        if method == "eth_call":
            to, data = params[0]["to"], params[0]["data"]
            if to == self.feeds.get(chain):
                return hex(int(PRICE * 1e8))
            if self.usdc.get(chain) and to.lower() == self.usdc[chain].lower():
                for (c, a), v in self.erc20.items():
                    if c == chain and data == self.fk.encode_call("balanceOf(address)", a):
                        return hex(v)
                return "0x0"
            raise AssertionError(f"unexpected eth_call to {to}")
        if method == "eth_getBalance":
            return hex(self.native.get((chain, params[0]), 0))
        if method == "eth_getTransactionCount":
            return hex(7 + self.sends.get(chain, 0))
        if method == "eth_gasPrice":
            return hex(10**7)
        if method == "eth_sendRawTransaction":
            self.sends[chain] = self.sends.get(chain, 0) + 1
            h = "0x" + hashlib.sha256(f"{chain}{self.sends[chain]}".encode()).hexdigest()
            self.sent.append((chain, h))
            return h
        if method == "eth_getTransactionReceipt":
            if self.receipt_mode == "none":
                return None
            return {"status": "0x1" if self.receipt_mode == "ok" else "0x0"}
        if method == "eth_getTransactionByHash":
            return {"nonce": hex(7)}
        raise AssertionError(f"unexpected rpc {method}")


def fake_priv(label):
    return hashlib.sha256(("farm-test:" + label).encode()).digest()


def setup(tmp):
    g_mod = load(GATE_PATH, f"gatectl_{abs(hash(tmp))}")
    ws = os.path.join(tmp, "ws")
    state = os.path.join(tmp, "state")
    for d in (state, f"{ws}/bots/paper", f"{ws}/bots/live", f"{ws}/bots/archive"):
        os.makedirs(d, exist_ok=True)
    g_mod.WS, g_mod.STATE = ws, state
    g_mod.PAPER, g_mod.LIVE, g_mod.ARCHIVE = f"{ws}/bots/paper", f"{ws}/bots/live", f"{ws}/bots/archive"
    g_mod.LOG, g_mod.PNL = f"{state}/gate.log", f"{state}/pnl.json"
    cfg = {"chains": ["ethereum", "base", "arbitrum"], "max_capital_usd": 2000, "max_daily_loss_usd": 200,
           "max_loss_per_tx_usd": 50, "max_capital_per_bot_usd": 400, "gas_wallet_cap_usd": {"base": 18},
           "usdc": {"base": USDC_BASE}, "relay_url": "http://fake"}
    chain = FakeChain(g_mod.farmkeys, g_mod.ETH_USD_FEED, cfg["usdc"])
    g = g_mod.Gate.__new__(g_mod.Gate)
    g.cfg, g.rpc, g._price, g.master = cfg, chain, {}, None
    g.key = lambda label, create=False: fake_priv(label)

    class Sub:
        calls = []

        @staticmethod
        def run(args, **kw):
            Sub.calls.append(args)
            if "/opt/farm/bin/gate-root" in args and "adopt" in args:
                raise Reached("adopt")

            class R:
                returncode, stdout, stderr = 0, "", ""
            return R()
    g_mod.subprocess = Sub
    return g_mod, g, chain


def gate_log(g_mod):
    if not os.path.exists(g_mod.LOG):
        return []
    return [json.loads(x) for x in open(g_mod.LOG)]


MANIFEST = """id: mw
chains:
  - base
strategy: test
capital_usd: 120
principal_usdc: 0            # flash loan
allowed_contracts:
  - 0x1111111111111111111111111111111111111111   # pool
max_loss_per_tx_usd: 20
"""

RESULTS = []


def case(name):
    def deco(fn):
        def run():
            clock = FakeClock()
            real = (time.monotonic, time.sleep)
            time.monotonic, time.sleep = clock.monotonic, clock.sleep
            err = io.StringIO()
            try:
                with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stderr(err):
                    fn(tmp)
                RESULTS.append((name, True, ""))
            except SystemExit as exc:
                RESULTS.append((name, False, f"exited: {err.getvalue().strip() or exc}"))
            except Exception as exc:
                RESULTS.append((name, False, f"{type(exc).__name__}: {exc}"))
            finally:
                time.monotonic, time.sleep = real
        return run
    return deco


@case("promote: capped Base share (120 -> 18 USD) passes with 21.25 USD on the intermediate")
def t_promote_capped(tmp):
    g_mod, g, chain = setup(tmp)
    os.makedirs(f"{g_mod.PAPER}/mw")
    open(f"{g_mod.PAPER}/mw/manifest.yaml", "w").write(MANIFEST)
    chain.native[("base", g.intermediate())] = chain.usd_wei(21.25)
    try:
        g.promote("mw")
    except Reached:
        return
    raise AssertionError("promote returned without reaching adopt")


@case("promote: with 10 USD on the intermediate it refuses and names the cap")
def t_promote_short(tmp):
    g_mod, g, chain = setup(tmp)
    os.makedirs(f"{g_mod.PAPER}/mw")
    open(f"{g_mod.PAPER}/mw/manifest.yaml", "w").write(MANIFEST)
    chain.native[("base", g.intermediate())] = chain.usd_wei(10)
    err = io.StringIO()
    try:
        with contextlib.redirect_stderr(err):
            g.promote("mw")
    except SystemExit:
        msg = err.getvalue()
        assert "18.00 USD" in msg and "gas wallet cap" in msg, msg
        return
    except Reached:
        raise AssertionError("passed the funding check with 10 USD")
    raise AssertionError("no refusal")


def live_bot_with_usdc(g_mod, g, chain, usdc_raw=100_000_000):
    os.makedirs(f"{g_mod.LIVE}/mw/state")
    open(f"{g_mod.LIVE}/mw/manifest.yaml", "w").write(MANIFEST)
    bot = g.addr("bot:mw")
    chain.native[("base", bot)] = chain.usd_wei(18)
    chain.erc20[("base", bot)] = usdc_raw
    p = g.pnl()
    p["baseline"]["mw"] = {"base": chain.usd_wei(18)}
    p.setdefault("baseline_usdc", {})["mw"] = {"base": 100_000_000}
    g.save_pnl(p)
    return bot


@case("sweep: bot holding USDC sweeps both, books 0 USD, logs both nonces")
def t_sweep_ok(tmp):
    g_mod, g, chain = setup(tmp)
    live_bot_with_usdc(g_mod, g, chain)
    with contextlib.redirect_stdout(io.StringIO()):
        g.sweep("mw")
    ops = {r["op"]: r for r in gate_log(g_mod)}
    assert "sweep_usdc_sent" in ops and ops["sweep_usdc_sent"]["nonce"] == 7, ops
    assert ops["sweep_usdc"]["usd"] == 0.0 and ops["sweep_usdc"]["nonce"] == 7, ops["sweep_usdc"]
    assert ops["sweep"]["nonce"] == 8, ops["sweep"]
    p = json.load(open(g_mod.PNL))
    assert p["realized_usd"]["mw"] == 0.0, p
    assert "mw" not in p["baseline_usdc"] and "mw" not in p["baseline"], p


@case("sweep: USDC receipt not back -> in flight; next day's sweep books 0, not -100 (no phantom loss)")
def t_sweep_pending(tmp):
    g_mod, g, chain = setup(tmp)
    bot = live_bot_with_usdc(g_mod, g, chain)
    chain.receipt_mode = "none"
    with contextlib.redirect_stdout(io.StringIO()):
        g.sweep("mw")
    p = json.load(open(g_mod.PNL))
    assert p["usdc_in_flight"]["mw"]["base"]["usdc"] == 100_000_000, p
    assert p["baseline_usdc"]["mw"]["base"] == 100_000_000, p
    # the transfer is mined later; a UTC day passes; someone sweeps again
    chain.erc20[("base", bot)] = 0
    chain.receipt_mode = "ok"
    p["day"] = "2000-01-01"
    json.dump(p, open(g_mod.PNL, "w"))
    with contextlib.redirect_stdout(io.StringIO()):
        g.sweep("mw")
    p = json.load(open(g_mod.PNL))
    assert p["realized_usd"].get("mw", 0.0) == 0.0 or abs(p["realized_usd"]["mw"]) < 1, p
    assert not any(r.get("note") == "principal gone" for r in gate_log(g_mod)), "phantom loss booked"
    assert "mw" not in p.get("usdc_in_flight", {}), p


@case("sweep: reverted USDC transfer -> failed, baseline kept, nothing booked")
def t_sweep_revert(tmp):
    g_mod, g, chain = setup(tmp)
    live_bot_with_usdc(g_mod, g, chain)
    chain.receipt_mode = "revert"
    with contextlib.redirect_stdout(io.StringIO()):
        g.sweep("mw")
    p = json.load(open(g_mod.PNL))
    assert p["baseline_usdc"]["mw"]["base"] == 100_000_000, p
    assert "mw" not in p["realized_usd"], p
    assert any(r["op"] == "sweep_failed" and "reverted" in r["why"] for r in gate_log(g_mod))


@case("stop --all: an exception on one bot does not stop the loop")
def t_stop_all(tmp):
    g_mod, g, chain = setup(tmp)
    for b in ("aaa-bot", "bbb-bot"):
        os.makedirs(f"{g_mod.LIVE}/{b}")
    seen = []

    def stop(b):
        seen.append(b)
        if b == "aaa-bot":
            raise RuntimeError("rpc down")
    g.stop = stop
    with contextlib.redirect_stdout(io.StringIO()):
        g.stop_all()
    assert seen == ["aaa-bot", "bbb-bot"], seen


@case("watchdog: chains read from block, inline, quoted and scalar styles")
def t_watchdog(tmp):
    wd = load(WD_PATH, f"watchdog_{abs(hash(tmp))}")
    styles = {
        "chains:\n  - base\n  - ethereum   # comment\nother: 1\n": ["base", "ethereum"],
        "chains: [ethereum, base]\n": ["ethereum", "base"],
        'chains: ["arbitrum"]\n': ["arbitrum"],
        "chains: base\n": ["base"],
    }
    for text, want in styles.items():
        got = wd.manifest_chains(text)
        assert got == want, f"{text!r}: got {got}, want {want}"
    assert "sweep_usdc_sent" in open(WD_PATH).read()


for fn in list(globals().values()):
    if callable(fn) and getattr(fn, "__name__", "") == "run":
        fn()

label = "phase 9g (before)" if OLD else "phase 9i"
print(f"== {label}: {os.path.basename(GATE_PATH)} / {os.path.basename(WD_PATH)}")
for name, ok, why in RESULTS:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"\n        {why}" if why else ""))
failed = [r for r in RESULTS if not r[1]]
if not OLD:
    print("ALL PASS" if not failed else f"{len(failed)} FAILED")
    sys.exit(1 if failed else 0)
