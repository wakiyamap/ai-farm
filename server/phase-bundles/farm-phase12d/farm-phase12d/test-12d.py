#!/usr/bin/env python3
"""Phase 12d offline tests: no RPC, no keys, no files outside a temp directory.

  test-12d.py <gate-ctl> <farm-watchdog> <farmchains_dir> [--old]

Drives Gate (promote / status / stop with exitAll) and the watchdog's main loop against fake
chains. --old runs the same cases against the installed files and only reports (the failures
there are what 12d adds; the cases marked "as before" must pass on both); otherwise any failure
exits 1.
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
sys.dont_write_bytecode = True               # do not leave __pycache__ next to the installed programs
if len(args) != 3:
    sys.exit(__doc__)
GATE_PATH, WD_PATH, FC_DIR = args
sys.path.insert(0, FC_DIR)
STUB = os.environ.get("FARMKEYS_STUB")      # local development only; the server uses /opt/farm/pylib
if STUB:
    sys.path.insert(0, STUB)
import farmchains  # noqa: E402

RESULTS = []
PRICE = 2000.0
USDC = {"ethereum": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48", "base": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"}
A1 = "0x1111111111111111111111111111111111111111"
FRAME = {"max_holding_usd_total": 200, "max_holding_usd_per_bot": 100}
SIGNED = []                                   # every tx dict handed to farmkeys.sign_eip1559, with its sender
REAL_SIGN = [None]


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
    """Fake relay. A send moves the sender's nonce; balances change only when a test (or its
    on_send hook) changes them."""

    def __init__(self, fk):
        self.fk = fk
        self.native, self.erc20, self.nonces = {}, {}, {}
        self.sends, self.receipts = [], {}
        self.fail = None                     # fn(chain, method, params) -> exception to raise, or None
        self.on_send = None                  # fn(record): a test's model of what the tx does
        self.status = lambda rec: "0x1"      # receipt status of a sent tx; None = never mined

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
            frm, tx = SIGNED[-1]
            rec = {"chain": chain, "from": frm, "to": tx.get("to"), "data": tx.get("data"), "nonce": tx.get("nonce"),
                   "gas": tx.get("gas"), "hash": "0x" + hashlib.sha256(f"{chain}{len(self.sends)}".encode()).hexdigest()}
            self.sends.append(rec)
            self.nonces[(chain, frm)] = self.nonces.get((chain, frm), 0) + 1
            self.receipts[rec["hash"]] = self.status(rec)
            if self.on_send and self.receipts[rec["hash"]] == "0x1":
                self.on_send(rec)
            return rec["hash"]
        if method == "eth_getTransactionReceipt":
            st = self.receipts.get(params[0], "0x1")
            return {"status": st} if st else None
        raise AssertionError(f"unexpected rpc {method}")


# --- gate -------------------------------------------------------------------------------------

def gate_setup(tmp, frame=True):
    g_mod = load(GATE_PATH, "gate")
    fk = g_mod.farmkeys
    if REAL_SIGN[0] is None:
        REAL_SIGN[0] = fk.sign_eip1559

    def sign(priv, tx):
        SIGNED.append((fk.address_of(priv), dict(tx)))
        return REAL_SIGN[0](priv, tx)
    fk.sign_eip1559 = sign
    ws, state = os.path.join(tmp, "ws"), os.path.join(tmp, "state")
    for d in (state, f"{ws}/bots/paper", f"{ws}/bots/live", f"{ws}/bots/archive", f"{ws}/scratch/x"):
        os.makedirs(d, exist_ok=True)
    g_mod.WS, g_mod.STATE = ws, state
    g_mod.PAPER, g_mod.LIVE, g_mod.ARCHIVE = f"{ws}/bots/paper", f"{ws}/bots/live", f"{ws}/bots/archive"
    g_mod.LOG, g_mod.PNL = f"{state}/gate.log", f"{state}/pnl.json"
    exit_all = {"type": "function", "name": "exitAll", "inputs": [], "outputs": [], "stateMutability": "nonpayable"}
    buy = {"type": "function", "name": "buy", "inputs": [{"name": "maxUsdc", "type": "uint256"}], "outputs": []}
    for name, abi in (("H.json", [buy, exit_all]), ("E.json", [buy]),
                      ("X.json", [buy, dict(exit_all, inputs=[{"name": "minOut", "type": "uint256"}])])):
        with open(f"{ws}/scratch/x/{name}", "w") as f:
            json.dump({"bytecode": {"object": "0x6080604052" + "00" * 40}, "abi": abi}, f)
    chain = Chain(fk)
    g = g_mod.Gate.__new__(g_mod.Gate)
    g.cfg = {"chains": ["ethereum", "base"], "max_capital_usd": 2000, "max_daily_loss_usd": 200,
             "max_loss_per_tx_usd": 50, "max_capital_per_bot_usd": 400, "gas_wallet_cap_usd": {"base": 18},
             "usdc": dict(USDC), "relay_url": "http://fake"}
    if frame:
        g.cfg.update(FRAME)
    g.rpc, g._price, g.master = chain, {}, None
    g.key = lambda label, create=False: fake_priv(label)

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
    inter = g.intermediate()
    chain.native[("ethereum", inter)], chain.native[("base", inter)] = wei(300), wei(100)
    chain.erc20[("ethereum", inter)], chain.erc20[("base", inter)] = 400 * 10**6, 400 * 10**6
    return g_mod, g, chain, Sub


def manifest(bid, holding=20, principal=20, capital=40, hours=24, artifact="H.json", chains="ethereum", extra=""):
    lines = [f"id: {bid}", f"chains: [{chains}]", "strategy: t", f"capital_usd: {capital}", "max_loss_per_tx_usd: 20",
             "allowed_contracts: []"]
    if principal is not None:
        lines.append(f"principal_usdc: {principal}")
    if holding is not None:
        lines.append(f"holding_usd: {holding}")
    if hours is not None:
        lines.append(f"holding_max_hours: {hours}")
    if artifact:
        lines.append(f"executor: scratch/x/{artifact}")
    return "\n".join(lines) + "\n" + extra


def paper_bot(g_mod, bid, text):
    d = f"{g_mod.PAPER}/{bid}"
    os.makedirs(d)
    with open(f"{d}/manifest.yaml", "w") as f:
        f.write(text)
    with open(f"{d}/bot.js", "w") as f:
        f.write("const exec = process.env.EXECUTOR_ADDR;\n")


def gate_log(g_mod, op=None):
    if not os.path.exists(g_mod.LOG):
        return []
    return [r for r in map(json.loads, open(g_mod.LOG)) if op is None or r.get("op") == op]


def pnl(g_mod):
    return json.load(open(g_mod.PNL))


def refused(g, g_mod, chain, sub, bid, word):
    """promote must refuse before anything moves, and say why."""
    err = io.StringIO()
    try:
        with contextlib.redirect_stderr(err):
            g.promote(bid)
    except SystemExit:
        assert word in err.getvalue(), f"refused, but not for this reason: {err.getvalue().strip()[-200:]}"
        assert not chain.sends, chain.sends
        assert os.path.isdir(f"{g_mod.PAPER}/{bid}") and not any("adopt" in a for a in sub.calls)
        return
    raise AssertionError("promoted")


def promoted_holding_bot(tmp, bid="hold1", holding=20, held=True, chains="ethereum", **kw):
    """A holding bot promoted through the gate. With held=True its USDC principal has left the
    wallet (it is "another asset" in the executor) and exitAll() brings 19 of the 20 back."""
    g_mod, g, chain, sub = gate_setup(tmp, **kw)
    paper_bot(g_mod, bid, manifest(bid, holding=holding, principal=holding, capital=holding + 20, chains=chains))
    g.promote(bid)
    a = g.addr(f"bot:{bid}")
    ex = {r["chain"]: r["address"] for r in gate_log(g_mod, "deploy_executor")}
    for c in chains.split(", "):
        chain.native[(c, a)] = pnl(g_mod)["baseline"][bid][c]          # the gas float is untouched
        chain.erc20[(c, a)] = 0 if held else holding * 10**6

    def on_send(rec):
        if rec["to"] == ex.get(rec["chain"]) and rec["from"] == a:
            chain.erc20[(rec["chain"], a)] = (holding - 1) * 10**6
    chain.on_send = on_send if held else None
    chain.sends.clear()
    return g_mod, g, chain, sub, a, ex


def stop_code(g, bid, **kw):
    try:
        g.stop(bid, **kw)
        return 0
    except SystemExit as exc:
        return exc.code


@case("gate promote: a holding bot (holding_usd 20, principal_usdc 20, executor with exitAll()) is promoted; "
      "the promote record carries holding_usd")
def t_promote_ok(tmp):
    g_mod, g, chain, _ = gate_setup(tmp)
    paper_bot(g_mod, "hold1", manifest("hold1"))
    g.promote("hold1")
    assert os.path.exists(f"{g_mod.LIVE}/hold1/state/executor.json")
    assert gate_log(g_mod, "promote")[-1].get("holding_usd") == 20, gate_log(g_mod, "promote")
    assert pnl(g_mod)["baseline_usdc"]["hold1"]["ethereum"] == 20 * 10**6


@case("gate promote: refused when the live holding_usd (100 + 90) plus the new bot's 20 would pass 200; "
      "with 80 live it goes through (100 + 80 + 20 = 200)")
def t_promote_total(tmp):
    g_mod, g, chain, sub = gate_setup(tmp)
    for bid, h in (("big1", 100), ("big2", 90)):
        os.makedirs(f"{g_mod.LIVE}/{bid}/state")
        with open(f"{g_mod.LIVE}/{bid}/manifest.yaml", "w") as f:
            f.write(manifest(bid, holding=h, principal=h, capital=h + 20))
    paper_bot(g_mod, "hold3", manifest("hold3"))
    refused(g, g_mod, chain, sub, "hold3", "max_holding_usd_total")
    with open(f"{g_mod.LIVE}/big2/manifest.yaml", "w") as f:
        f.write(manifest("big2", holding=80, principal=80, capital=100))
    g.promote("hold3")
    assert os.path.isdir(f"{g_mod.LIVE}/hold3")


@case("gate promote: holding_usd 120 is refused (per-bot limit 100)")
def t_promote_per_bot(tmp):
    g_mod, g, chain, sub = gate_setup(tmp)
    paper_bot(g_mod, "fat1", manifest("fat1", holding=120, principal=120, capital=140))
    refused(g, g_mod, chain, sub, "fat1", "per-bot limit")


@case("gate promote: holding_usd above principal_usdc is refused")
def t_promote_principal(tmp):
    g_mod, g, chain, sub = gate_setup(tmp)
    paper_bot(g_mod, "thin1", manifest("thin1", holding=50, principal=20, capital=60))
    refused(g, g_mod, chain, sub, "thin1", "principal_usdc")


@case("gate promote: a holding bot without an executor is refused")
def t_promote_no_executor(tmp):
    g_mod, g, chain, sub = gate_setup(tmp)
    paper_bot(g_mod, "eoa1", manifest("eoa1", artifact=None).replace("allowed_contracts: []", f"allowed_contracts: [{A1}]"))
    refused(g, g_mod, chain, sub, "eoa1", "needs an executor")


@case("gate promote: an executor without exitAll(), or whose exitAll takes arguments, is refused")
def t_promote_no_exit(tmp):
    g_mod, g, chain, sub = gate_setup(tmp)
    paper_bot(g_mod, "noex1", manifest("noex1", artifact="E.json"))
    paper_bot(g_mod, "noex2", manifest("noex2", artifact="X.json"))
    refused(g, g_mod, chain, sub, "noex1", "exitAll()")
    refused(g, g_mod, chain, sub, "noex2", "exitAll()")


@case("gate promote: holding_max_hours missing, 0 or above 168 (7 days) is refused; 168 is accepted")
def t_promote_hours(tmp):
    g_mod, g, chain, sub = gate_setup(tmp)
    for bid, h in (("hrs1", None), ("hrs2", 0), ("hrs3", 169)):
        paper_bot(g_mod, bid, manifest(bid, hours=h))
        refused(g, g_mod, chain, sub, bid, "holding_max_hours")
    paper_bot(g_mod, "hrs4", manifest("hrs4", hours=168))
    g.promote("hrs4")


@case("gate promote: a holding bot is refused while gate.json has no max_holding_usd_* keys (frame not enabled)")
def t_promote_frame_off(tmp):
    g_mod, g, chain, sub = gate_setup(tmp, frame=False)
    paper_bot(g_mod, "hold1", manifest("hold1"))
    refused(g, g_mod, chain, sub, "hold1", "not enabled")


@case("gate promote: holding_usd that is not a number (abc, -5) is refused")
def t_promote_bad_value(tmp):
    g_mod, g, chain, sub = gate_setup(tmp)
    paper_bot(g_mod, "bad1", manifest("bad1", holding="abc"))
    paper_bot(g_mod, "bad2", manifest("bad2", holding=-5))
    refused(g, g_mod, chain, sub, "bad1", "holding_usd")
    refused(g, g_mod, chain, sub, "bad2", "holding_usd")


@case("gate promote, as before: a bot without holding_usd is promoted, with or without the frame in gate.json; "
      "holding_usd: 0, or the key left empty as in the template, is the same")
def t_promote_plain(tmp):
    for frame in (True, False):
        g_mod, g, chain, _ = gate_setup(os.path.join(tmp, str(frame)), frame=frame)
        paper_bot(g_mod, "plain1", manifest("plain1", holding=None, hours=None, artifact="E.json"))
        paper_bot(g_mod, "zero1", manifest("zero1", holding=0, hours=None, artifact="E.json"))
        paper_bot(g_mod, "blank1", manifest("blank1", holding="", hours="", artifact="E.json"))
        g.promote("plain1")
        g.promote("zero1")
        g.promote("blank1")
        assert pnl(g_mod)["baseline"]["plain1"]["ethereum"] > 0


@case("gate status: shows the frame (per-bot holding_usd, total, the two limits)")
def t_status(tmp):
    g_mod, g, chain, sub, a, ex = promoted_holding_bot(tmp)
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        g.status()
    st = json.loads(out.getvalue())
    assert st["holding_usd"] == {"live": {"hold1": 20.0}, "total": 20.0, "max_total": 200, "max_per_bot": 100}, st.get("holding_usd")


@case("gate stop: for a holding bot, exitAll() goes to the executor from the bot key BEFORE the sweep; "
      "exit_sent (with nonce) and exit are logged; the returned 19 USDC are swept and booked (-1 USD); archived")
def t_stop_exit(tmp):
    g_mod, g, chain, sub, a, ex = promoted_holding_bot(tmp)
    n0 = chain.nonces[("ethereum", a)]
    assert stop_code(g, "hold1") == 0
    assert os.path.isdir(f"{g_mod.ARCHIVE}/hold1")
    first = chain.sends[0]
    assert first["to"] == ex["ethereum"] and first["from"] == a, first
    assert first["data"] == g_mod.farmkeys.selector("exitAll()"), first["data"]
    assert [s["to"].lower() for s in chain.sends[1:]] == [USDC["ethereum"].lower(), g.intermediate().lower()], chain.sends
    sent, done = gate_log(g_mod, "exit_sent"), gate_log(g_mod, "exit")
    assert [r["nonce"] for r in sent] == [n0] and [r["nonce"] for r in done] == [n0], (sent, done)
    assert done[0]["usdc_back"] == 19 * 10**6 and done[0]["executor"] == ex["ethereum"], done
    p = pnl(g_mod)
    assert abs(p["realized_usd"]["hold1"] + 1.0) < 0.01, p["realized_usd"]       # 20 funded, 19 back; gas float untouched
    assert not gate_log(g_mod, "stop_incomplete")


@case("gate stop: when exitAll() does not estimate (it would revert), no transaction is sent at all, nothing "
      "is swept, the bot stays live, exit code 3, exit_failed and stop_incomplete are logged, baselines untouched")
def t_stop_exit_no_estimate(tmp):
    g_mod, g, chain, sub, a, ex = promoted_holding_bot(tmp)
    before = pnl(g_mod)
    chain.fail = lambda c, m, p: RuntimeError("execution reverted") if m == "eth_estimateGas" and p[0].get("to") == ex["ethereum"] else None
    assert stop_code(g, "hold1") == 3
    assert not chain.sends, chain.sends
    assert os.path.isdir(f"{g_mod.LIVE}/hold1") and not os.path.isdir(f"{g_mod.ARCHIVE}/hold1")
    assert gate_log(g_mod, "exit_failed") and gate_log(g_mod, "stop_incomplete") and not gate_log(g_mod, "stop")
    after = pnl(g_mod)
    assert after["baseline"] == before["baseline"] and after["baseline_usdc"] == before["baseline_usdc"]
    assert not after["realized_usd"], after["realized_usd"]
    assert any("disable" in c for c in sub.calls), "the service was not stopped"


@case("gate stop: exitAll() mined but reverted -> exit code 3, exit_failed carries the nonce and the tx hash, "
      "nothing is swept; a second `gate stop` after the cause is gone exits, sweeps and archives")
def t_stop_exit_reverted(tmp):
    g_mod, g, chain, sub, a, ex = promoted_holding_bot(tmp)
    n0 = chain.nonces[("ethereum", a)]
    chain.status = lambda rec: "0x0" if rec["to"] == ex["ethereum"] else "0x1"
    assert stop_code(g, "hold1") == 3
    f = gate_log(g_mod, "exit_failed")
    assert len(f) == 1 and f[0]["nonce"] == n0 and f[0].get("txHash"), f
    assert len(chain.sends) == 1 and os.path.isdir(f"{g_mod.LIVE}/hold1"), chain.sends
    chain.status = lambda rec: "0x1"
    assert stop_code(g, "hold1") == 0
    assert os.path.isdir(f"{g_mod.ARCHIVE}/hold1")
    assert abs(pnl(g_mod)["realized_usd"]["hold1"] + 1.0) < 0.01, pnl(g_mod)["realized_usd"]


@case("gate stop: exitAll() sent but not mined in time -> exit code 3, the nonce is in gate.log, nothing is swept")
def t_stop_exit_pending(tmp):
    g_mod, g, chain, sub, a, ex = promoted_holding_bot(tmp)
    n0 = chain.nonces[("ethereum", a)]
    chain.status = lambda rec: None
    real_mono, t = time.monotonic, [0.0]

    def mono():
        t[0] += 30.0                          # poll_receipt gives up after its timeout without real waiting
        return t[0]
    time.monotonic = mono
    try:
        code = stop_code(g, "hold1")
    finally:
        time.monotonic = real_mono
    assert code == 3
    assert [r["nonce"] for r in gate_log(g_mod, "exit_sent")] == [n0]
    assert [r["nonce"] for r in gate_log(g_mod, "exit_failed")] == [n0]
    assert len(chain.sends) == 1 and os.path.isdir(f"{g_mod.LIVE}/hold1")


@case("gate stop: the send call itself fails (relay timeout) -> exit_failed with the nonce (the call may be out), "
      "exit code 3")
def t_stop_exit_send_fails(tmp):
    g_mod, g, chain, sub, a, ex = promoted_holding_bot(tmp)
    n0 = chain.nonces[("ethereum", a)]
    chain.fail = lambda c, m, p: TimeoutError("timed out") if m == "eth_sendRawTransaction" else None
    assert stop_code(g, "hold1") == 3
    assert [r.get("nonce") for r in gate_log(g_mod, "exit_failed")] == [n0], gate_log(g_mod, "exit_failed")
    assert os.path.isdir(f"{g_mod.LIVE}/hold1")


@case("gate stop: after 3 exitAll() transactions that failed on chain, a 4th is not sent (the watchdog repeats "
      "unfinished stops every 10 min); `--exit-again` sends one more")
def t_stop_exit_cap(tmp):
    g_mod, g, chain, sub, a, ex = promoted_holding_bot(tmp)
    chain.status = lambda rec: "0x0" if rec["to"] == ex["ethereum"] else "0x1"
    for _ in range(3):
        assert stop_code(g, "hold1") == 3
    assert len(chain.sends) == 3, len(chain.sends)
    assert stop_code(g, "hold1") == 3
    assert len(chain.sends) == 3, "a 4th exitAll() was sent without --exit-again"
    chain.status = lambda rec: "0x1"
    assert stop_code(g, "hold1", exit_again=True) == 0
    assert os.path.isdir(f"{g_mod.ARCHIVE}/hold1")


@case("gate stop: exitAll() mined, but the executor still holds USDC -> exit code 3, nothing is swept")
def t_stop_exit_left(tmp):
    g_mod, g, chain, sub, a, ex = promoted_holding_bot(tmp)
    chain.erc20[("ethereum", ex["ethereum"])] = 7 * 10**6
    assert stop_code(g, "hold1") == 3
    f = gate_log(g_mod, "exit_failed")
    assert len(f) == 1 and "still holds 7.00 USDC" in f[0]["why"], f
    assert len(chain.sends) == 1 and os.path.isdir(f"{g_mod.LIVE}/hold1")


@case("gate stop: a holding bot whose gas float is spent gets a top-up from the intermediate wallet first "
      "(added to its baseline), then exitAll()")
def t_stop_exit_topup(tmp):
    g_mod, g, chain, sub, a, ex = promoted_holding_bot(tmp)
    chain.native[("ethereum", a)] = 1000
    base0 = pnl(g_mod)["baseline"]["hold1"]["ethereum"]

    def on_send(rec):
        if rec["to"] == a:                                    # the top-up arrives
            chain.native[("ethereum", a)] += wei(5)
        if rec["to"] == ex["ethereum"]:
            chain.erc20[("ethereum", a)] = 19 * 10**6
    chain.on_send = on_send
    assert stop_code(g, "hold1") == 0
    assert chain.sends[0]["from"] == g.intermediate() and chain.sends[0]["to"] == a, chain.sends[0]
    assert chain.sends[1]["to"] == ex["ethereum"], chain.sends[1]
    top = gate_log(g_mod, "exit_gas_topup")
    assert len(top) == 1 and top[0]["wei"] > 0, top
    assert os.path.isdir(f"{g_mod.ARCHIVE}/hold1")
    assert base0 > 0


@case("gate stop: exitAll() whose worst-case gas is above L (50 USD) is not sent; exit code 3")
def t_stop_exit_gas_over_l(tmp):
    g_mod, g, chain, sub, a, ex = promoted_holding_bot(tmp)
    chain.fail = None
    real = chain.call

    def call(c, m, p, lane="live"):
        if m == "eth_gasPrice":
            return hex(50 * 10**9)                            # 50 gwei: 600,000 gas is about 130 USD at the cap
        return real(c, m, p, lane)
    chain.call = call
    assert stop_code(g, "hold1") == 3
    assert not chain.sends, chain.sends
    assert "above L" in gate_log(g_mod, "exit_failed")[0]["why"]


@case("gate stop: on two chains, a failed exit on one still tries the other; nothing is swept; exit code 3")
def t_stop_exit_two_chains(tmp):
    g_mod, g, chain, sub, a, ex = promoted_holding_bot(tmp, chains="ethereum, base")
    chain.fail = lambda c, m, p: RuntimeError("execution reverted") if (c, m) == ("base", "eth_estimateGas") and p[0].get("to") == ex["base"] else None
    assert stop_code(g, "hold1") == 3
    assert [(s["chain"], s["to"]) for s in chain.sends] == [("ethereum", ex["ethereum"])], chain.sends
    assert [r["chain"] for r in gate_log(g_mod, "exit")] == ["ethereum"]
    assert [r["chain"] for r in gate_log(g_mod, "exit_failed")] == ["base"]
    assert os.path.isdir(f"{g_mod.LIVE}/hold1")


@case("gate stop: the executor address comes from gate.log; an address planted in the bot-writable "
      "state/executor.json is never called")
def t_stop_exit_planted(tmp):
    g_mod, g, chain, sub, a, ex = promoted_holding_bot(tmp)
    with open(f"{g_mod.LIVE}/hold1/state/executor.json", "w") as f:
        json.dump({"ethereum": {"address": A1, "nonce": 0, "txHash": "0x00"},
                   "base": {"address": A1, "nonce": 5, "txHash": "0x00"}}, f)
    assert stop_code(g, "hold1") == 0
    assert A1 not in [s["to"] for s in chain.sends], chain.sends
    assert chain.sends[0]["to"] == ex["ethereum"]


@case("gate stop: a holding bot promoted again under the same id uses its new executor, and failures counted "
      "before the last archive do not count")
def t_stop_exit_same_id(tmp):
    g_mod, g, chain, sub, a, ex = promoted_holding_bot(tmp)
    chain.status = lambda rec: "0x0" if rec["to"] == ex["ethereum"] else "0x1"
    for _ in range(3):
        assert stop_code(g, "hold1") == 3
    chain.status = lambda rec: "0x1"
    assert stop_code(g, "hold1", exit_again=True) == 0
    os.rename(f"{g_mod.ARCHIVE}/hold1", f"{g_mod.ARCHIVE}/hold1-old")
    paper_bot(g_mod, "hold1", manifest("hold1"))
    g.promote("hold1")
    ex2 = gate_log(g_mod, "deploy_executor")[-1]["address"]
    assert ex2 != ex["ethereum"]
    chain.sends.clear()
    assert stop_code(g, "hold1") == 0
    assert chain.sends[0]["to"] == ex2, chain.sends[0]


@case("gate stop: a holding bot whose executor was never deployed (promotion cut short) has nothing to exit: "
      "exit_skipped, then the usual sweep and archive")
def t_stop_exit_skipped(tmp):
    g_mod, g, chain, sub = gate_setup(tmp)
    os.makedirs(f"{g_mod.LIVE}/half1/state")
    with open(f"{g_mod.LIVE}/half1/manifest.yaml", "w") as f:
        f.write(manifest("half1"))
    a = g.addr("bot:half1")
    chain.native[("ethereum", a)], chain.erc20[("ethereum", a)] = wei(10), 20 * 10**6
    g.save_pnl({"day": time.strftime("%Y-%m-%d", time.gmtime()), "realized_usd": {},
                "baseline": {"half1": {"ethereum": wei(10)}}, "baseline_usdc": {"half1": {"ethereum": 20 * 10**6}}})
    assert stop_code(g, "half1") == 0
    assert gate_log(g_mod, "exit_skipped") and os.path.isdir(f"{g_mod.ARCHIVE}/half1")
    assert [s["to"].lower() for s in chain.sends] == [USDC["ethereum"].lower(), g.intermediate().lower()], chain.sends


@case("gate stop, as before: a bot without holding_usd is swept and archived with no exitAll() call, even if "
      "its executor has one")
def t_stop_plain(tmp):
    g_mod, g, chain, sub = gate_setup(tmp)
    paper_bot(g_mod, "plain1", manifest("plain1", holding=None, hours=None))
    g.promote("plain1")
    a = g.addr("bot:plain1")
    chain.native[("ethereum", a)], chain.erc20[("ethereum", a)] = wei(22), 19 * 10**6
    chain.sends.clear()
    g.stop("plain1")
    assert os.path.isdir(f"{g_mod.ARCHIVE}/plain1")
    assert [s["to"].lower() for s in chain.sends] == [USDC["ethereum"].lower(), g.intermediate().lower()], chain.sends
    p = pnl(g_mod)
    assert abs(p["realized_usd"]["plain1"] - 1.0) < 0.01, p["realized_usd"]      # -1 USDC, +2 native
    assert not gate_log(g_mod, "exit_sent") and not gate_log(g_mod, "exit_skipped")


@case("gate stop --all: a holding bot whose exit fails stays live; the other bots are still stopped")
def t_stop_all(tmp):
    g_mod, g, chain, sub, a, ex = promoted_holding_bot(tmp)
    paper_bot(g_mod, "plain1", manifest("plain1", holding=None, hours=None))
    g.promote("plain1")
    b = g.addr("bot:plain1")
    chain.native[("ethereum", b)] = wei(20)
    chain.fail = lambda c, m, p: RuntimeError("execution reverted") if m == "eth_estimateGas" and p[0].get("to") == ex["ethereum"] else None
    g.stop_all()
    assert os.path.isdir(f"{g_mod.LIVE}/hold1") and os.path.isdir(f"{g_mod.ARCHIVE}/plain1")
    assert os.path.exists(f"{g_mod.STATE}/halt")


# --- watchdog ---------------------------------------------------------------------------------

def run_loop(tmp, bots, pnl_data, rounds, step=None, signer_log=(), gate_log_recs=(), cfg_extra=FRAME):
    """bots: {id: (manifest text, {chain: [wei, usdc_raw, nonce]})}; step(round, state) mutates them."""
    wd = load(WD_PATH, "wd")
    live, state = os.path.join(tmp, "live"), os.path.join(tmp, "state")
    os.makedirs(state)
    for b, (text, _) in bots.items():
        os.makedirs(f"{live}/{b}")
        with open(f"{live}/{b}/manifest.yaml", "w") as f:
            f.write(text)
    if pnl_data is not None:
        with open(f"{state}/pnl.json", "w") as f:
            json.dump(pnl_data, f)
    for name, recs in (("signer.log", signer_log), ("gate.log", gate_log_recs)):
        with open(f"{state}/{name}", "w") as f:
            for r in recs:
                f.write(json.dumps(r) + "\n")
    conf = os.path.join(tmp, "gate.json")
    with open(conf, "w") as f:
        json.dump(dict({"relay_url": "x", "watchdog_interval_s": 15, "usdc": dict(USDC), "max_loss_per_tx_usd": 50,
                        "max_daily_loss_usd": 200, "max_live_loss_usd": 30}, **(cfg_extra or {})), f)
    wd.CONF, wd.LIVE, wd.STATE, wd.INBOX = conf, live, state, os.path.join(tmp, "inbox")
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
            step(n[0], st)
    wd.time.sleep = sleep
    try:
        wd.main()
    except Stop:
        pass
    inbox = wd.INBOX
    wakes = [open(f"{inbox}/{f}").read() for f in sorted(os.listdir(inbox))] if os.path.isdir(inbox) else []
    return stops, wakes


def wd_manifest(holding=None):
    return "chains: [ethereum]\n" + (f"holding_usd: {holding}\n" if holding is not None else "")


def bot(holding, usdc_now, native_usd=10):
    return {"b1": (wd_manifest(holding), {"ethereum": [wei(native_usd), usdc_now * 10**6, 3]})}


BASE100 = {"baseline": {"b1": {"ethereum": wei(10)}}, "baseline_usdc": {"b1": {"ethereum": 100 * 10**6}}}


def buy(amount):
    def step(r, st):
        if r == 1:
            st[("b1", "ethereum")][1] -= amount * 10**6
            st[("b1", "ethereum")][2] += 1
    return step


SENT3 = [{"bot": "b1", "op": "send", "decision": "sent", "chain": "ethereum", "nonce": 3}]


@case("watchdog: a holding bot (holding_usd 100) that moves 100 USDC into its executor in one interval is "
      "not stopped (before: stopped at once, as a 100 USD drop above L and a 100 USD loss above 30)")
def t_wd_buy(tmp):
    stops, wakes = run_loop(tmp, bot(100, 100), BASE100, rounds=4, step=buy(100), signer_log=SENT3)
    assert stops == [], (stops, wakes)


@case("watchdog: holding_usd 100 -> the live-loss stop is at 130: a loss of 125 does not stop, 135 does, and "
      "the wake message names the line")
def t_wd_line(tmp):
    stops, _ = run_loop(os.path.join(tmp, "a"), bot(100, 100), BASE100, rounds=4, step=buy(125), signer_log=SENT3)
    assert stops == [], stops
    stops, wakes = run_loop(os.path.join(tmp, "b"), bot(100, 100), BASE100, rounds=4, step=buy(135), signer_log=SENT3)
    assert stops == ["b1"], stops
    assert any("limit 130 USD = 30 + holding_usd 100" in w for w in wakes), wakes


@case("watchdog: holding_usd 20 -> stop at 50: a loss of 45 does not stop, 55 does")
def t_wd_line_20(tmp):
    base = {"baseline": {"b1": {"ethereum": wei(10)}}, "baseline_usdc": {"b1": {"ethereum": 60 * 10**6}}}
    stops, _ = run_loop(os.path.join(tmp, "a"), bot(20, 60), base, rounds=4, step=buy(45), signer_log=SENT3)
    assert stops == [], stops
    stops, _ = run_loop(os.path.join(tmp, "b"), bot(20, 60), base, rounds=4, step=buy(55), signer_log=SENT3)
    assert stops == ["b1"], stops


@case("watchdog: a manifest claiming holding_usd 500 is held to the per-bot limit (100): stop at 130")
def t_wd_cap(tmp):
    base = {"baseline": {"b1": {"ethereum": wei(10)}}, "baseline_usdc": {"b1": {"ethereum": 300 * 10**6}}}
    stops, _ = run_loop(tmp, bot(500, 300), base, rounds=4, step=buy(135), signer_log=SENT3)
    assert stops == ["b1"], stops


@case("watchdog: while gate.json has no max_holding_usd_per_bot, holding_usd is ignored: a 35 USD loss stops")
def t_wd_frame_off(tmp):
    stops, _ = run_loop(tmp, bot(100, 100), BASE100, rounds=4, step=buy(35), signer_log=SENT3, cfg_extra=None)
    assert stops == ["b1"], stops


@case("watchdog: an unreadable holding_usd (abc, -5, nan) counts as 0: a 35 USD loss stops")
def t_wd_bad_value(tmp):
    for i, v in enumerate(("abc", -5, "nan")):
        stops, _ = run_loop(os.path.join(tmp, str(i)), bot(v, 100), BASE100, rounds=4, step=buy(35), signer_log=SENT3)
        assert stops == ["b1"], (v, stops)


@case("watchdog, as before: a bot without holding_usd is stopped by a 35 USD loss since promotion, and by a "
      "60 USD drop between two reads")
def t_wd_plain(tmp):
    stops, wakes = run_loop(os.path.join(tmp, "a"), bot(None, 100), BASE100, rounds=4, step=buy(35), signer_log=SENT3)
    assert stops == ["b1"] and any("limit 30 USD;" in w for w in wakes), (stops, wakes)
    stops, _ = run_loop(os.path.join(tmp, "b"), bot(None, 100), None, rounds=4, step=buy(60), signer_log=SENT3)
    assert stops == ["b1"], stops


@case("watchdog, as before: a 25 USD loss stops nobody")
def t_wd_small(tmp):
    stops, _ = run_loop(tmp, bot(None, 100), BASE100, rounds=4, step=buy(25), signer_log=SENT3)
    assert stops == [], stops


def bump(r, st):
    if r == 1:
        st[("b1", "ethereum")][2] += 1


@case("watchdog: the nonce of the gate's exitAll() (exit_sent in gate.log) is not a key compromise")
def t_wd_exit_sent(tmp):
    stops, _ = run_loop(tmp, bot(20, 0), None, rounds=3, step=bump,
                        gate_log_recs=[{"bot": "b1", "op": "exit_sent", "chain": "ethereum", "nonce": 3, "txHash": "0x1"}])
    assert "--all" not in stops, "halted everything over the gate's own exitAll()"


@case("watchdog: the nonce in an exit_failed record (send call failed, but mined) is not a key compromise")
def t_wd_exit_failed(tmp):
    stops, _ = run_loop(tmp, bot(20, 0), None, rounds=3, step=bump,
                        gate_log_recs=[{"bot": "b1", "op": "exit_failed", "chain": "ethereum", "nonce": 3, "why": "x"}])
    assert "--all" not in stops, "halted everything over the gate's own exitAll()"


@case("watchdog, as before: a nonce found in no log still halts everything (an exit_failed record without a "
      "nonce, or for another bot, does not cover it)")
def t_wd_unknown(tmp):
    stops, wakes = run_loop(tmp, bot(20, 0), None, rounds=3, step=bump,
                            gate_log_recs=[{"bot": "b1", "op": "exit_failed", "chain": "ethereum", "why": "no estimate"},
                                           {"bot": "b2", "op": "exit_sent", "chain": "ethereum", "nonce": 3}])
    assert "--all" in stops and wakes, stops


for fn in list(globals().values()):
    if callable(fn) and getattr(fn, "__name__", "") == "run":
        fn()

print(f"== {'before 12d (installed files)' if OLD else 'phase 12d'}")
for name, ok, why in RESULTS:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"\n        {why}" if why else ""))
failed = [r for r in RESULTS if not r[1]]
print(f"{len(RESULTS) - len(failed)} of {len(RESULTS)} passed" + (" (installed files: failures expected)" if OLD else ""))
if not OLD:
    print("ALL PASS" if not failed else f"{len(failed)} FAILED")
    sys.exit(1 if failed else 0)
