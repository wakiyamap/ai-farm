#!/usr/bin/env python3
"""Phase 10g offline tests: elysium on the money path (no RPC, no keys, temp dirs only).

  test-10g.py <gate-ctl> <farm-signer> <farm-watchdog> <farmchains_dir> [--old]

<farmchains_dir> must hold the 10g farmchains.py (the bundle directory): the tests load it before
the programs do, so the programs under test see the elysium entry.
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
if len(args) != 4:
    sys.exit(__doc__)
GATE_PATH, SIGNER_PATH, WD_PATH, FC_DIR = args
sys.path.insert(0, FC_DIR)
STUB = os.environ.get("FARMKEYS_STUB")      # local development only; the server uses /opt/farm/lib
if STUB:
    sys.path.insert(0, STUB)
import farmchains  # noqa: E402

RESULTS = []
HYPE, ETH = 74.0, 2000.0
USDC = {"elysium": "0xb47c4C8F73F009CC0C0d3f92B388d13E293F0B65", "base": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"}
A1 = "0x1111111111111111111111111111111111111111"
FEED = farmchains.ETH_USD_FEED


def load(path, tag):
    name = f"{tag}_{time.time_ns()}"
    loader = importlib.machinery.SourceFileLoader(name, path)
    mod = importlib.util.module_from_spec(importlib.util.spec_from_loader(name, loader))
    loader.exec_module(mod)
    return mod


def fake_priv(label):
    return hashlib.sha256(("farm-test:" + label).encode()).digest()


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
    """Fake relay. Elysium has no price feed: reading the feed address there fails, as on the real
    chain (no contract). A plain transfer costs 21,140 gas on elysium."""

    def __init__(self, fk):
        self.fk = fk
        self.native, self.erc20, self.down = {}, {}, set()
        self.sends, self.feed_reads = [], []

    def call(self, chain, method, params, lane="live"):
        if chain in self.down:
            raise RuntimeError("all providers failed")
        if method == "eth_call":
            to, data = params[0]["to"].lower(), params[0]["data"]
            if to == FEED["hyperevm"].lower() or to == FEED.get(chain, "").lower():
                self.feed_reads.append(chain)
                if chain == "elysium":
                    raise RuntimeError("execution reverted")            # no feed contract on elysium
                if data == self.fk.selector("decimals()"):
                    return hex(8)
                if data == self.fk.selector("description()"):
                    d = farmchains.CHAINS[chain]["desc"][-1].encode()
                    return "0x" + (32).to_bytes(32, "big").hex() + len(d).to_bytes(32, "big").hex() + d.ljust(32, b"\0").hex()
                return hex(int((HYPE if chain == "hyperevm" else ETH) * 1e8))
            if to == USDC.get(chain, "").lower():
                for (c, a), v in self.erc20.items():
                    if c == chain and data == self.fk.encode_call("balanceOf(address)", a):
                        return hex(v)
                return "0x0"
            raise AssertionError(f"unexpected eth_call to {to} on {chain}")
        if method == "eth_getBalance":
            return hex(self.native.get((chain, params[0]), 0))
        if method == "eth_getTransactionCount":
            return hex(0)
        if method in ("eth_gasPrice", "eth_maxPriorityFeePerGas"):
            return hex(10**8)
        if method == "eth_estimateGas":
            p = params[0]
            if "to" not in p:
                return hex(400_000)                          # contract creation
            return hex(60_000 if p.get("data", "0x") != "0x" else (21_140 if chain == "elysium" else 21_000))
        if method == "eth_sendRawTransaction":
            self.sends.append(chain)
            return "0x" + hashlib.sha256(f"{chain}{len(self.sends)}".encode()).hexdigest()
        if method == "eth_getTransactionReceipt":
            return {"status": "0x1"}
        raise AssertionError(f"unexpected rpc {method}")


def gate_setup(tmp):
    g_mod = load(GATE_PATH, "gate")
    ws, state = os.path.join(tmp, "ws"), os.path.join(tmp, "state")
    for d in (state, f"{ws}/bots/paper", f"{ws}/bots/live", f"{ws}/bots/archive"):
        os.makedirs(d, exist_ok=True)
    g_mod.WS, g_mod.STATE = ws, state
    g_mod.PAPER, g_mod.LIVE, g_mod.ARCHIVE = f"{ws}/bots/paper", f"{ws}/bots/live", f"{ws}/bots/archive"
    g_mod.LOG, g_mod.PNL = f"{state}/gate.log", f"{state}/pnl.json"
    chain = Chain(g_mod.farmkeys)
    g = g_mod.Gate.__new__(g_mod.Gate)
    g.cfg = {"chains": ["ethereum", "base", "hyperevm", "elysium"], "max_capital_usd": 2000, "max_daily_loss_usd": 200,
             "max_loss_per_tx_usd": 50, "max_capital_per_bot_usd": 400, "gas_wallet_cap_usd": {"base": 18},
             "usdc": dict(USDC), "relay_url": "http://fake"}
    g.rpc, g._price, g.master = chain, {}, None
    g.key = lambda label, create=False: fake_priv(label)
    g.wait_receipt = lambda *a, **k: {"status": "0x1"}

    class Sub:
        @staticmethod
        def run(a, **kw):
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
    txs = []
    real_sign = g_mod.farmkeys.sign_eip1559

    def sign(priv, tx):
        txs.append(dict(tx))
        return real_sign(priv, tx)
    g_mod.farmkeys.sign_eip1559 = sign
    return g_mod, g, chain, txs, real_sign


def manifest(bid, chain, principal=0):
    return (f"id: {bid}\nchains: [{chain}]\nstrategy: t\ncapital_usd: {20 + principal}\nmax_loss_per_tx_usd: 20\n"
            + (f"principal_usdc: {principal}\n" if principal else "") + f"allowed_contracts: [{A1}]\n")


def hype(usd):
    return int(usd / HYPE * 1e18)


@case("gate: elysium is priced with the HYPE / USD feed read on hyperevm (never on elysium itself)")
def t_gate_price(tmp):
    g_mod, g, chain, txs, real = gate_setup(tmp)
    try:
        assert abs(g.eth_usd("elysium") - HYPE) < 1e-6
        assert chain.feed_reads == ["hyperevm"], chain.feed_reads
    finally:
        g_mod.farmkeys.sign_eip1559 = real


@case("gate: promote on elysium funds HYPE and USDC with estimated gas limits (a 21,000 transfer is rejected there)")
def t_gate_promote(tmp):
    g_mod, g, chain, txs, real = gate_setup(tmp)
    try:
        inter = g.intermediate()
        chain.native[("elysium", inter)], chain.erc20[("elysium", inter)] = hype(100), 200 * 10**6
        os.makedirs(f"{g_mod.PAPER}/ely1")
        with open(f"{g_mod.PAPER}/ely1/manifest.yaml", "w") as f:
            f.write(manifest("ely1", "elysium", principal=50))
        g.promote("ely1")
        native_tx = [t for t in txs if t["data"] == "0x"][0]
        usdc_tx = [t for t in txs if t["data"] != "0x"][0]
        assert native_tx["chainId"] == 99901 and native_tx["gas"] > 21_140, native_tx
        assert abs(native_tx["value"] - hype(20)) < 10**12, native_tx["value"]
        assert 60_000 < usdc_tx["gas"] <= 300_000, usdc_tx["gas"]
        p = json.load(open(g_mod.PNL))
        assert p["baseline_usdc"]["ely1"]["elysium"] == 50 * 10**6
    finally:
        g_mod.farmkeys.sign_eip1559 = real


@case("gate: sweep on elysium signs the gas limit it reserved, and value + gas * maxFee fits the balance")
def t_gate_sweep(tmp):
    g_mod, g, chain, txs, real = gate_setup(tmp)
    try:
        os.makedirs(f"{g_mod.LIVE}/ely2/state")
        with open(f"{g_mod.LIVE}/ely2/manifest.yaml", "w") as f:
            f.write(manifest("ely2", "elysium"))
        a = g.addr("bot:ely2")
        bal = hype(19)
        chain.native[("elysium", a)] = bal
        g.save_pnl({"day": time.strftime("%Y-%m-%d", time.gmtime()), "realized_usd": {},
                    "baseline": {"ely2": {"elysium": hype(20)}}, "baseline_usdc": {}})
        assert g.sweep("ely2") is True
        t = txs[-1]
        assert t["gas"] > 21_140 and t["value"] + t["gas"] * t["maxFeePerGas"] <= bal, t
        p = json.load(open(g_mod.PNL))
        assert abs(p["realized_usd"]["ely2"] + 1.0) < 0.01, p["realized_usd"]
    finally:
        g_mod.farmkeys.sign_eip1559 = real


@case("gate: an emptied elysium wallet the node will not estimate for is still swept to a booked loss, not an error")
def t_gate_dust(tmp):
    g_mod, g, chain, txs, real = gate_setup(tmp)
    try:
        os.makedirs(f"{g_mod.LIVE}/ely3/state")
        with open(f"{g_mod.LIVE}/ely3/manifest.yaml", "w") as f:
            f.write(manifest("ely3", "elysium"))
        g.save_pnl({"day": time.strftime("%Y-%m-%d", time.gmtime()), "realized_usd": {},
                    "baseline": {"ely3": {"elysium": hype(20)}}, "baseline_usdc": {}})
        orig = chain.call

        def call(c, method, params, lane="live"):
            if method == "eth_estimateGas":
                raise RuntimeError("insufficient funds for gas * price + value")
            return orig(c, method, params, lane)
        chain.call = call
        assert g.sweep("ely3") is True
        assert abs(json.load(open(g_mod.PNL))["realized_usd"]["ely3"] + 20.0) < 0.01
    finally:
        g_mod.farmkeys.sign_eip1559 = real


@case("gate: base and ethereum transfers keep the fixed 21,000 gas (no estimate call)")
def t_gate_base(tmp):
    g_mod, g, chain, txs, real = gate_setup(tmp)
    try:
        inter = g.intermediate()
        chain.native[("base", inter)] = int(0.05 * 1e18)
        os.makedirs(f"{g_mod.PAPER}/b1")
        with open(f"{g_mod.PAPER}/b1/manifest.yaml", "w") as f:
            f.write(manifest("b1", "base"))
        g.promote("b1")
        assert txs[-1]["gas"] == 21000 and txs[-1]["chainId"] == 8453, txs[-1]
    finally:
        g_mod.farmkeys.sign_eip1559 = real


def signer_setup(tmp):
    s_mod = load(SIGNER_PATH, "signer")
    fk = s_mod.farmkeys
    fk.derive_private_key = lambda master, label, create=False: fake_priv(label)
    chain = Chain(fk)
    s = s_mod.Signer.__new__(s_mod.Signer)
    s.cfg = {"max_loss_per_tx_usd": 50, "gas_wallet_cap_usd": {"base": 18}, "usdc": dict(USDC)}
    s.master, s.rpc = None, chain
    s.prices = s_mod.Prices(chain)
    s.prices.disabled = {}
    s.spend = lambda: {"day": "x", "bots": {}}
    s_mod.STATE = tmp
    s_mod.LOG = os.path.join(tmp, "signer.log")
    return s_mod, s, chain


@case("signer: an elysium transaction is priced in HYPE from hyperevm; 1 HYPE of gas (74 USD) exceeds L=50")
def t_signer_price(tmp):
    s_mod, s, chain = signer_setup(tmp)
    m = {"chains": ["elysium"], "allowed_contracts": [A1], "capital_usd": 400}
    ok = {"chain": "elysium", "to": A1, "gas": hex(500_000), "maxFeePerGas": hex(10**9)}
    assert s.check("b", ok, m, "0x" + "ab" * 20) is None
    assert chain.feed_reads == ["hyperevm"], chain.feed_reads
    big = {"chain": "elysium", "to": A1, "gas": hex(1_000_000), "maxFeePerGas": hex(10**12)}
    why = s.check("b", big, m, "0x" + "ab" * 20)
    assert why and "exceeds L" in why, why


@case("signer: feed check at start accepts elysium through hyperevm; with hyperevm unreadable both are disabled, "
      "the core chains still sign")
def t_signer_feeds(tmp):
    s_mod, s, chain = signer_setup(tmp)
    s.prices.verify_feeds()
    assert s.prices.disabled == {}, s.prices.disabled
    chain.down = {"hyperevm"}
    s.prices.verify_feeds()
    assert set(s.prices.disabled) == {"hyperevm", "elysium"}, s.prices.disabled
    m = {"chains": ["elysium"], "allowed_contracts": [A1], "capital_usd": 400}
    why = s.check("b", {"chain": "elysium", "to": A1, "gas": hex(1), "maxFeePerGas": hex(1)}, m, "0x" + "ab" * 20)
    assert why and "disabled" in why, why


@case("watchdog: an elysium bot is read (price from hyperevm) and a 60 USD drop in one interval stops it")
def t_watchdog(tmp):
    wd = load(WD_PATH, "wd")
    live, state = os.path.join(tmp, "live"), os.path.join(tmp, "state")
    os.makedirs(f"{live}/ely1")
    os.makedirs(state)
    with open(f"{live}/ely1/manifest.yaml", "w") as f:
        f.write("chains: [elysium]\n")
    conf = os.path.join(tmp, "gate.json")
    with open(conf, "w") as f:
        json.dump({"relay_url": "x", "watchdog_interval_s": 15, "usdc": dict(USDC), "max_loss_per_tx_usd": 50,
                   "max_daily_loss_usd": 200, "max_live_loss_usd": 30}, f)
    wd.CONF, wd.LIVE, wd.STATE, wd.INBOX = conf, live, state, os.path.join(tmp, "inbox")
    wd.farmkeys.load_master = lambda: None
    wd.farmkeys.derive_private_key = lambda master, label, create=False: fake_priv(label)
    chain = Chain(wd.farmkeys)
    addr = wd.farmkeys.address_of(fake_priv("bot:ely1"))
    chain.native[("elysium", addr)] = hype(100)
    wd.rpc = lambda url, c, method, params: chain.call(c, method, params)
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
        chain.native[("elysium", addr)] = hype(40)
        if n[0] >= 2:
            raise Stop()
    wd.time.sleep = sleep
    try:
        wd.main()
    except Stop:
        pass
    assert stops == ["ely1"], f"stops {stops}, feed reads {set(chain.feed_reads)}"
    assert set(chain.feed_reads) == {"hyperevm"}, chain.feed_reads


for fn in list(globals().values()):
    if callable(fn) and getattr(fn, "__name__", "") == "run":
        fn()

print(f"== {'before 10g (installed files, 10g farmchains)' if OLD else 'phase 10g'}")
for name, ok, why in RESULTS:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"\n        {why}" if why else ""))
failed = [r for r in RESULTS if not r[1]]
if not OLD:
    print("ALL PASS" if not failed else f"{len(failed)} FAILED")
    sys.exit(1 if failed else 0)
