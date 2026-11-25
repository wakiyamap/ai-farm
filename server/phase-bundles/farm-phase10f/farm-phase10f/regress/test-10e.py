#!/usr/bin/env python3
"""Phase 10e offline tests: no RPC, no keys, no files outside a temp directory.

  test-10e.py <gate-ctl> <farm-signer> <farm-watchdog> <farmchains_dir> [--old]

Drives Gate (promote / fund / sweep / stop), the signer's policy and send path, and the watchdog's
main loop against fake chains. --old runs the same cases against the installed files and only
reports (the failures there are what 10e fixes); otherwise any failure exits 1.
"""
import contextlib
import hashlib
import importlib.machinery
import importlib.util
import io
import json
import os
import shutil
import sys
import tempfile
import threading
import time

args = [a for a in sys.argv[1:] if a != "--old"]
OLD = "--old" in sys.argv
sys.dont_write_bytecode = True               # do not leave __pycache__ next to the installed programs
if len(args) != 4:
    sys.exit(__doc__)
GATE_PATH, SIGNER_PATH, WD_PATH, FC_DIR = args
sys.path.insert(0, FC_DIR)
STUB = os.environ.get("FARMKEYS_STUB")      # local development only; the server uses /opt/farm/lib
if STUB:
    sys.path.insert(0, STUB)
import farmchains  # noqa: E402

RESULTS = []
PRICE = 2000.0
USDC = {"base": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913", "arbitrum": "0xaf88d065e77c8cC2239327C5EDb3A432268e5831"}
A1 = "0x1111111111111111111111111111111111111111"
A2 = "0x2222222222222222222222222222222222222222"


def load(path, tag):
    name = f"{tag}_{time.time_ns()}"
    loader = importlib.machinery.SourceFileLoader(name, path)
    mod = importlib.util.module_from_spec(importlib.util.spec_from_loader(name, loader))
    loader.exec_module(mod)
    return mod


def fake_priv(label):
    return hashlib.sha256(("farm-test:" + label).encode()).digest()


def wei(usd):
    return int(usd / PRICE * 1e18)


class Stop(BaseException):
    pass


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
    """Fake relay. Balances and nonces only change when a test changes them."""

    def __init__(self, fk):
        self.fk = fk
        self.native, self.erc20, self.nonces = {}, {}, {}
        self.sends = []
        self.fail = None                     # fn(chain, method, params) -> exception to raise, or None

    def call(self, chain, method, params, lane="live"):
        exc = self.fail(chain, method, params) if self.fail else None
        if exc:
            raise exc
        if method == "eth_call":
            to, data = params[0]["to"].lower(), params[0]["data"]
            if to == farmchains.ETH_USD_FEED[chain].lower():
                return hex(int(PRICE * 1e8))
            if to == USDC.get(chain, "").lower():
                for (c, a), v in self.erc20.items():
                    if c == chain and data == self.fk.encode_call("balanceOf(address)", a):
                        return hex(v)
                return "0x0"
            raise AssertionError(f"unexpected eth_call to {to} on {chain}")
        if method == "eth_getBalance":
            return hex(self.native.get((chain, params[0]), 0))
        if method == "eth_getTransactionCount":
            return hex(self.nonces.get((chain, params[0]), 0))
        if method == "eth_gasPrice":
            return hex(10**8)
        if method == "eth_estimateGas":
            return hex(400_000)
        if method == "eth_sendRawTransaction":
            self.sends.append(chain)
            return "0x" + hashlib.sha256(f"{chain}{len(self.sends)}".encode()).hexdigest()
        if method == "eth_getTransactionReceipt":
            return {"status": "0x1"}
        raise AssertionError(f"unexpected rpc {method}")


# --- gate -------------------------------------------------------------------------------------

def gate_setup(tmp):
    g_mod = load(GATE_PATH, "gate")
    ws, state = os.path.join(tmp, "ws"), os.path.join(tmp, "state")
    for d in (state, f"{ws}/bots/paper", f"{ws}/bots/live", f"{ws}/bots/archive", f"{ws}/scratch/x"):
        os.makedirs(d, exist_ok=True)
    g_mod.WS, g_mod.STATE = ws, state
    g_mod.PAPER, g_mod.LIVE, g_mod.ARCHIVE = f"{ws}/bots/paper", f"{ws}/bots/live", f"{ws}/bots/archive"
    g_mod.LOG, g_mod.PNL = f"{state}/gate.log", f"{state}/pnl.json"
    with open(f"{ws}/scratch/x/E.json", "w") as f:
        json.dump({"bytecode": {"object": "0x6080604052" + "00" * 40}}, f)
    chain = Chain(g_mod.farmkeys)
    g = g_mod.Gate.__new__(g_mod.Gate)
    g.cfg = {"chains": ["ethereum", "base", "arbitrum"], "max_capital_usd": 2000, "max_daily_loss_usd": 200,
             "max_loss_per_tx_usd": 50, "max_capital_per_bot_usd": 400, "gas_wallet_cap_usd": {"base": 18},
             "usdc": dict(USDC), "relay_url": "http://fake"}
    g.rpc, g._price, g.master = chain, {}, None
    g.key = lambda label, create=False: fake_priv(label)
    g.wait_receipt = lambda *a, **k: {"status": "0x1"}

    class Sub:
        calls = []

        @staticmethod
        def run(a, **kw):
            Sub.calls.append(a)
            out = ""
            if "/opt/farm/bin/gate-root" in a and "adopt" in a:
                os.rename(f"{g_mod.PAPER}/{a[-1]}", f"{g_mod.LIVE}/{a[-1]}")
                os.makedirs(f"{g_mod.LIVE}/{a[-1]}/state", exist_ok=True)
            if "/opt/farm/bin/gate-root" in a and "archive" in a:
                os.rename(f"{g_mod.LIVE}/{a[-1]}", f"{g_mod.ARCHIVE}/{a[-1]}")
                out = f"bots/archive/{a[-1]}"

            class R:
                returncode, stdout, stderr = 0, out, ""
            return R()
    g_mod.subprocess = Sub
    chain.native[("ethereum", g.intermediate())] = wei(600)
    chain.native[("arbitrum", g.intermediate())] = wei(100)
    chain.native[("base", g.intermediate())] = wei(100)
    return g_mod, g, chain, Sub


def paper_bot(g_mod, bid, manifest, files):
    d = f"{g_mod.PAPER}/{bid}"
    os.makedirs(d)
    with open(f"{d}/manifest.yaml", "w") as f:
        f.write(manifest)
    for name, text in files.items():
        os.makedirs(os.path.dirname(f"{d}/{name}"), exist_ok=True)
        with open(f"{d}/{name}", "w") as f:
            f.write(text)


def live_bot(g_mod, bid, chains):
    os.makedirs(f"{g_mod.LIVE}/{bid}/state")
    with open(f"{g_mod.LIVE}/{bid}/manifest.yaml", "w") as f:
        f.write(f"id: {bid}\nchains: [{', '.join(chains)}]\ncapital_usd: 100\nallowed_contracts: [{A1}]\n")


def gate_log(g_mod, op):
    if not os.path.exists(g_mod.LOG):
        return []
    return [r for r in map(json.loads, open(g_mod.LOG)) if r.get("op") == op]


def pnl(g_mod):
    return json.load(open(g_mod.PNL))


def day():
    return time.strftime("%Y-%m-%d", time.gmtime())


EXEC = "id: {id}\nchains: [ethereum]\nstrategy: t\ncapital_usd: 20\nmax_loss_per_tx_usd: 20\nallowed_contracts: []\n" \
       "executor: scratch/x/E.json\n"


@case("gate: an executor bot that reads EXEC_ADDRESS (the 11-10 reserve-dutch bug) is refused before any funds move")
def t_exec_refused(tmp):
    g_mod, g, chain, sub = gate_setup(tmp)
    paper_bot(g_mod, "bad1", EXEC.format(id="bad1"),
              {"bot.js": "const exec = process.env.EXEC_ADDRESS;\n", "run.sh": "#!/bin/sh\nexec node bot.js\n",
               "README.md": "set EXECUTOR_ADDR\n"})          # a mention in docs does not count
    try:
        g.promote("bad1")
        raise AssertionError("promoted")
    except SystemExit:
        pass
    assert not chain.sends, chain.sends
    assert os.path.isdir(f"{g_mod.PAPER}/bad1") and not any("adopt" in a for a in sub.calls)


@case("gate: executor bots that read EXECUTOR_ADDR (bot.js) or state/executor.json (src/main.py) are promoted")
def t_exec_ok(tmp):
    g_mod, g, chain, _ = gate_setup(tmp)
    paper_bot(g_mod, "good1", EXEC.format(id="good1"), {"bot.js": "const exec = process.env.EXECUTOR_ADDR;\n"})
    paper_bot(g_mod, "good2", EXEC.format(id="good2"),
              {"src/main.py": "import json\nexec_addr = json.load(open('state/executor.json'))\n"})
    g.promote("good1")
    g.promote("good2")
    for b in ("good1", "good2"):
        assert os.path.exists(f"{g_mod.LIVE}/{b}/state/executor.json"), b


@case("gate: a bot without an executor needs no such code (allowed_contracts only) and is promoted as before")
def t_noexec_ok(tmp):
    g_mod, g, chain, _ = gate_setup(tmp)
    paper_bot(g_mod, "plain1", f"id: plain1\nchains: [ethereum]\ncapital_usd: 20\nmax_loss_per_tx_usd: 20\n"
                               f"allowed_contracts:\n  - {A1}\n", {"bot.js": "//\n"})
    g.promote("plain1")
    assert pnl(g_mod)["baseline"]["plain1"]["ethereum"] > 0


@case("gate: promote whose funding fails on the 2nd chain has already saved the 1st chain's baseline")
def t_promote_partial(tmp):
    g_mod, g, chain, _ = gate_setup(tmp)
    paper_bot(g_mod, "two1", f"id: two1\nchains: [ethereum, arbitrum]\ncapital_usd: 40\nmax_loss_per_tx_usd: 20\n"
                             f"allowed_contracts: [{A1}]\n", {"bot.js": "//\n"})
    chain.fail = lambda c, m, p: RuntimeError("all providers failed") if (c, m) == ("arbitrum", "eth_sendRawTransaction") else None
    try:
        g.promote("two1")
        raise AssertionError("promote did not fail")
    except RuntimeError:
        pass
    assert chain.sends == ["ethereum"], chain.sends
    assert os.path.exists(g_mod.PNL), "pnl.json not written: the funded bot has no baseline"
    assert pnl(g_mod)["baseline"]["two1"]["ethereum"] == wei(20)


@case("gate: fund refuses a top-up that would carry the bot past the 400 USD per-bot cap; a small one still goes")
def t_fund_cap(tmp):
    g_mod, g, chain, _ = gate_setup(tmp)
    live_bot(g_mod, "fat1", ["ethereum"])
    chain.native[("ethereum", g.addr("bot:fat1"))] = wei(380)
    try:
        g.fund("fat1", 50.0)
        raise AssertionError("funded past the cap")
    except SystemExit:
        pass
    assert not chain.sends, chain.sends
    g.fund("fat1", 10.0)
    assert chain.sends == ["ethereum"] and pnl(g_mod)["baseline"]["fat1"]["ethereum"] == wei(10)


@case("gate: stop with one chain unreadable keeps the other chain's booking, does not archive; the retry "
      "finishes without a phantom 'principal gone' loss")
def t_stop_incomplete(tmp):
    g_mod, g, chain, sub = gate_setup(tmp)
    live_bot(g_mod, "mix1", ["base", "arbitrum"])
    a = g.addr("bot:mix1")
    chain.native[("base", a)], chain.erc20[("base", a)] = wei(10), 52 * 10**6
    chain.native[("arbitrum", a)] = wei(10)
    g.save_pnl({"day": day(), "realized_usd": {}, "baseline": {"mix1": {"base": wei(10), "arbitrum": wei(10)}},
                "baseline_usdc": {"mix1": {"base": 50 * 10**6}}})
    chain.fail = lambda c, m, p: OSError("connection refused") if c == "arbitrum" else None
    try:
        g.stop("mix1")
        failed = False
    except (SystemExit, Exception):                        # noqa: BLE001
        failed = True
    assert failed, "stop reported success with arbitrum unreadable"
    assert os.path.isdir(f"{g_mod.LIVE}/mix1"), "archived although the arbitrum funds are still in the bot wallet"
    p = pnl(g_mod)
    assert abs(p["realized_usd"].get("mix1", 0) - 2.0) < 0.01, f"base USDC booking lost: {p['realized_usd']}"
    assert "base" not in p["baseline_usdc"].get("mix1", {})
    assert gate_log(g_mod, "stop_incomplete")
    chain.erc20[("base", a)], chain.native[("base", a)] = 0, 0       # those transfers were mined
    chain.fail = None
    g.stop("mix1")
    assert os.path.isdir(f"{g_mod.ARCHIVE}/mix1")
    p = pnl(g_mod)
    assert abs(p["realized_usd"]["mix1"] - 2.0) < 0.01, f"phantom loss: {p['realized_usd']}"
    assert "mix1" not in p["baseline"] and "mix1" not in p.get("baseline_usdc", {}), p


@case("gate: a bot that burned its whole gas float (18 USD on base) gets that loss booked at sweep")
def t_dust(tmp):
    g_mod, g, chain, _ = gate_setup(tmp)
    live_bot(g_mod, "dry1", ["base"])
    chain.native[("base", g.addr("bot:dry1"))] = 1000
    g.save_pnl({"day": day(), "realized_usd": {}, "baseline": {"dry1": {"base": wei(18)}}, "baseline_usdc": {}})
    assert g.sweep("dry1") is True
    p = pnl(g_mod)
    assert abs(p["realized_usd"].get("dry1", 0) + 18.0) < 0.01, p["realized_usd"]
    assert "dry1" not in p["baseline"], p["baseline"]


@case("gate: a native sweep whose send call failed but was mined is logged with its nonce and booked as "
      "returned, not as a 100 USD loss")
def t_unsure_native(tmp):
    g_mod, g, chain, _ = gate_setup(tmp)
    live_bot(g_mod, "uns1", ["ethereum"])
    a = g.addr("bot:uns1")
    chain.native[("ethereum", a)], chain.nonces[("ethereum", a)] = wei(98), 3
    g.save_pnl({"day": day(), "realized_usd": {}, "baseline": {"uns1": {"ethereum": wei(100)}}, "baseline_usdc": {}})
    chain.fail = lambda c, m, p: RuntimeError("all providers failed: alchemy: timed out") if m == "eth_sendRawTransaction" else None
    assert not g.sweep("uns1"), "sweep reported complete"
    assert [r.get("nonce") for r in gate_log(g_mod, "sweep_failed")] == [3], gate_log(g_mod, "sweep_failed")
    assert pnl(g_mod)["baseline"]["uns1"]["ethereum"] == wei(100)
    chain.fail = None
    chain.native[("ethereum", a)], chain.nonces[("ethereum", a)] = 0, 4          # it was mined after all
    assert g.sweep("uns1") is True
    p = pnl(g_mod)
    assert abs(p["realized_usd"]["uns1"] + 2.0) < 0.01, f"expected -2 USD, got {p['realized_usd']}"
    assert not p.get("sweep_unsure"), p.get("sweep_unsure")


@case("gate: the same for a USDC sweep (50 USDC principal): no 'principal gone' when the transfer was mined")
def t_unsure_usdc(tmp):
    g_mod, g, chain, _ = gate_setup(tmp)
    live_bot(g_mod, "uns2", ["arbitrum"])
    a = g.addr("bot:uns2")
    chain.native[("arbitrum", a)], chain.erc20[("arbitrum", a)], chain.nonces[("arbitrum", a)] = wei(5), 50 * 10**6, 7
    g.save_pnl({"day": day(), "realized_usd": {}, "baseline": {"uns2": {"arbitrum": wei(5)}},
                "baseline_usdc": {"uns2": {"arbitrum": 50 * 10**6}}})
    chain.fail = lambda c, m, p: TimeoutError("timed out") if m == "eth_sendRawTransaction" else None
    try:
        done = g.sweep("uns2")
    except OSError:
        done = False
    assert not done
    assert 7 in [r.get("nonce") for r in gate_log(g_mod, "sweep_failed")], gate_log(g_mod, "sweep_failed")
    chain.fail = None
    chain.erc20[("arbitrum", a)], chain.nonces[("arbitrum", a)] = 0, 8          # mined after all
    assert g.sweep("uns2") is True
    p = pnl(g_mod)
    assert abs(p["realized_usd"].get("uns2", 0)) < 0.01, f"phantom loss: {p['realized_usd']}"


@case("gate: an ordinary stop still sweeps USDC and native, books the PnL and archives")
def t_stop_ok(tmp):
    g_mod, g, chain, _ = gate_setup(tmp)
    live_bot(g_mod, "fine1", ["base"])
    a = g.addr("bot:fine1")
    chain.native[("base", a)], chain.erc20[("base", a)] = wei(12), 49 * 10**6
    g.save_pnl({"day": day(), "realized_usd": {}, "baseline": {"fine1": {"base": wei(10)}},
                "baseline_usdc": {"fine1": {"base": 50 * 10**6}}})
    g.stop("fine1")
    assert os.path.isdir(f"{g_mod.ARCHIVE}/fine1") and chain.sends == ["base", "base"], chain.sends
    p = pnl(g_mod)
    assert abs(p["realized_usd"]["fine1"] - 1.0) < 0.01, p["realized_usd"]          # -1 USDC, +2 native
    assert gate_log(g_mod, "stop") and not gate_log(g_mod, "stop_incomplete")


# --- signer -----------------------------------------------------------------------------------

def signer_setup(tmp):
    s_mod = load(SIGNER_PATH, "signer")
    fk = s_mod.farmkeys
    fk.derive_private_key = lambda master, label, create=False: fake_priv(label)   # no master in tests
    chain = Chain(fk)
    s = s_mod.Signer.__new__(s_mod.Signer)
    s.cfg = {"max_loss_per_tx_usd": 50, "gas_wallet_cap_usd": {"base": 18}, "usdc": dict(USDC)}
    s.master, s.rpc = None, chain
    s.prices = s_mod.Prices(chain)
    s.prices.disabled = {}
    s.lock = threading.Lock()
    s.spend = lambda: {"day": "x", "bots": {}}
    s.add_spend = lambda bot_id, usd: None
    s_mod.STATE = tmp
    s_mod.LOG = os.path.join(tmp, "signer.log")
    return s_mod, s, chain


@case("signer: increaseAllowance on USDC is held to the approve rule (unlisted spender refused, unlimited refused)")
def t_increase_allowance(tmp):
    s_mod, s, chain = signer_setup(tmp)
    sel = s_mod.farmkeys.selector("increaseAllowance(address,uint256)")
    m = {"chains": ["base"], "allowed_contracts": [A1], "capital_usd": 400}

    def req(spender, amount):
        return {"chain": "base", "to": USDC["base"], "gas": hex(100_000), "maxFeePerGas": hex(10**8),
                "data": sel + spender[2:].rjust(64, "0") + amount.to_bytes(32, "big").hex()}
    why = s.check("b", req(A2, 10 * 10**6), m, "0x" + "ab" * 20)
    assert why and "not allowed" in why, f"increaseAllowance to an unlisted spender passed: {why}"
    why = s.check("b", req(A1, (1 << 256) - 1), m, "0x" + "ab" * 20)
    assert why and "unlimited" in why, why
    assert s.check("b", req(A1, 10 * 10**6), m, "0x" + "ab" * 20) is None


@case("signer: a broadcast that dies with a socket timeout still leaves a broadcast_failed record with the nonce")
def t_broadcast_record(tmp):
    s_mod, s, chain = signer_setup(tmp)
    m = {"chains": ["ethereum"], "allowed_contracts": [A1], "capital_usd": 400}
    s.caller_bot = lambda conn: ("b", 0)
    s.manifest = lambda bot_id: m
    addr = s_mod.farmkeys.address_of(fake_priv("bot:b"))
    chain.nonces[("ethereum", addr)] = 9
    chain.fail = lambda c, mth, p: TimeoutError("timed out") if mth == "eth_sendRawTransaction" else None
    try:
        resp = s.handle(None, {"op": "send", "chain": "ethereum", "to": A1, "gas": hex(100_000), "maxFeePerGas": hex(10**9)})
    except OSError:
        resp = None
    recs = [json.loads(line) for line in open(s_mod.LOG)] if os.path.exists(s_mod.LOG) else []
    assert [r.get("nonce") for r in recs if r.get("decision") == "broadcast_failed"] == [9], recs
    assert resp and resp["ok"] is False, resp


# --- watchdog ---------------------------------------------------------------------------------

def run_loop(tmp, bots, pnl_data, rounds, step=None, signer_log=(), gate_log_recs=(), on_stop=None, retry_s=None,
             no_manifest=()):
    """bots: {id: (chains, {chain: [wei, usdc_raw, nonce]})}; step(round, state, live_dir) mutates them."""
    wd = load(WD_PATH, "wd")
    live, state = os.path.join(tmp, "live"), os.path.join(tmp, "state")
    os.makedirs(state)
    for b, (chains, _) in bots.items():
        os.makedirs(f"{live}/{b}")
        if b not in no_manifest:
            with open(f"{live}/{b}/manifest.yaml", "w") as f:
                f.write(f"chains: [{', '.join(chains)}]\n")
    if pnl_data is not None:
        with open(f"{state}/pnl.json", "w") as f:
            json.dump(pnl_data, f)
    for name, recs in (("signer.log", signer_log), ("gate.log", gate_log_recs)):
        with open(f"{state}/{name}", "w") as f:
            for r in recs:
                f.write(json.dumps(r) + "\n")
    conf = os.path.join(tmp, "gate.json")
    with open(conf, "w") as f:
        json.dump({"relay_url": "x", "watchdog_interval_s": 15, "usdc": dict(USDC), "max_loss_per_tx_usd": 50,
                   "max_daily_loss_usd": 200, "max_live_loss_usd": 30}, f)
    wd.CONF, wd.LIVE, wd.STATE, wd.INBOX = conf, live, state, os.path.join(tmp, "inbox")
    if retry_s is not None:
        wd.LOSS_RETRY_S = retry_s
    fk = wd.farmkeys
    fk.load_master = lambda: None
    fk.derive_private_key = lambda master, label, create=False: fake_priv(label)
    addr = {b: fk.address_of(fake_priv(f"bot:{b}")) for b in bots}
    st = {(b, c): list(v) for b, (_, vs) in bots.items() for c, v in vs.items()}

    def rpc(url, chain, method, params):
        who = next((b for b, a in addr.items() if a in json.dumps(params)), None)
        if method == "eth_getBalance":
            return hex(st[(who, chain)][0])
        if method == "eth_getTransactionCount":
            return hex(st[(who, chain)][2])
        if method == "eth_call":
            to = params[0]["to"].lower()
            if to == farmchains.ETH_USD_FEED[chain].lower():
                return hex(int(PRICE * 1e8))
            if to == USDC.get(chain, "").lower():
                b = next(b for b, a in addr.items() if params[0]["data"] == fk.encode_call("balanceOf(address)", a))
                return hex(st[(b, chain)][1])
        raise AssertionError(f"unexpected {method} {params}")
    wd.rpc = rpc
    stops = []

    class Sub:
        @staticmethod
        def run(a, **kw):
            if "/opt/farm/bin/gate-ctl" in a and "stop" in a:
                stops.append(a[-1])
                if on_stop:
                    on_stop(a[-1], live)

            class R:
                stdout, returncode = "", 0
            return R()
    wd.subprocess = Sub
    n = [0]

    def sleep(_):
        n[0] += 1
        if n[0] >= rounds:
            raise Stop()
        if step:
            step(n[0], st, live)
    wd.time.sleep = sleep
    try:
        wd.main()
    except Stop:
        pass
    wakes = os.listdir(wd.INBOX) if os.path.isdir(wd.INBOX) else []
    return stops, wakes


def bump_nonce(r, st, live):
    if r == 1:
        st[("b1", "ethereum")][2] += 1


ONE = {"b1": (["ethereum"], {"ethereum": [wei(50), 0, 3]})}


@case("watchdog: a nonce the signer logged as broadcast_failed (relay timeout, but mined) is not a key compromise")
def t_wd_broadcast_failed(tmp):
    stops, _ = run_loop(tmp, ONE, None, rounds=3, step=bump_nonce,
                        signer_log=[{"bot": "b1", "op": "send", "decision": "broadcast_failed", "chain": "ethereum", "nonce": 3}])
    assert "--all" not in stops, "halted everything over the signer's own transaction"


@case("watchdog: a nonce the gate logged in sweep_failed (send call failed, but mined) is not a key compromise")
def t_wd_sweep_failed(tmp):
    stops, _ = run_loop(tmp, ONE, None, rounds=3, step=bump_nonce,
                        gate_log_recs=[{"bot": "b1", "op": "sweep_failed", "chain": "ethereum", "nonce": 3, "why": "x"}])
    assert "--all" not in stops, "halted everything over the gate's own transfer"


@case("watchdog: a nonce found in no log still halts everything")
def t_wd_unknown(tmp):
    stops, wakes = run_loop(tmp, ONE, None, rounds=3, step=bump_nonce,
                            signer_log=[{"bot": "b1", "op": "send", "decision": "reject", "chain": "ethereum", "nonce": 3}],
                            gate_log_recs=[{"bot": "b1", "op": "sweep_failed", "chain": "ethereum", "why": "no nonce"}])
    assert "--all" in stops and wakes, stops


@case("watchdog: a live directory with an unreadable manifest does not hide a 60 USD drop of the bot after it")
def t_wd_bad_dir(tmp):
    def step(r, st, live):
        if r == 1:
            st[("b1", "ethereum")][0] -= wei(60)
    stops, _ = run_loop(tmp, {"a-broken": ([], {}), "b1": (["ethereum"], {"ethereum": [wei(100), 0, 3]})}, None,
                        rounds=3, step=step, no_manifest=("a-broken",))
    assert stops == ["b1"], stops


LOSS = {"b1": (["ethereum"], {"ethereum": [wei(60), 0, 3]})}
LOSS_PNL = {"baseline": {"b1": {"ethereum": wei(100)}}}


@case("watchdog: a live-loss stop that does not finish (bot still in bots/live) is tried again")
def t_wd_retry(tmp):
    stops, wakes = run_loop(tmp, LOSS, LOSS_PNL, rounds=5, retry_s=0)
    assert stops.count("b1") >= 2, f"gate stop tried {stops.count('b1')} time(s)"
    assert wakes


@case("watchdog: with the default 10 min between tries, 5 rounds call gate stop once")
def t_wd_retry_wait(tmp):
    stops, _ = run_loop(tmp, LOSS, LOSS_PNL, rounds=5)
    assert stops == ["b1"], stops


@case("watchdog: a bot stopped by the live-loss stop and promoted again under the same id is judged again")
def t_wd_same_id(tmp):
    def on_stop(bot, live):
        shutil.rmtree(f"{live}/{bot}")

    def step(r, st, live):
        if r == 3:
            os.makedirs(f"{live}/b1")
            with open(f"{live}/b1/manifest.yaml", "w") as f:
                f.write("chains: [ethereum]\n")
    stops, _ = run_loop(tmp, LOSS, LOSS_PNL, rounds=6, step=step, on_stop=on_stop)
    assert stops == ["b1", "b1"], stops


for fn in list(globals().values()):
    if callable(fn) and getattr(fn, "__name__", "") == "run":
        fn()

print(f"== {'before 10e (installed files)' if OLD else 'phase 10e'}")
for name, ok, why in RESULTS:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"\n        {why}" if why else ""))
failed = [r for r in RESULTS if not r[1]]
if not OLD:
    print("ALL PASS" if not failed else f"{len(failed)} FAILED")
    sys.exit(1 if failed else 0)
