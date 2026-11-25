#!/usr/bin/env python3
"""Phase 10b offline tests: no RPC, no keys, no files outside a temp directory.

  test-10b.py <gate-ctl> <farm-signer> <farm-watchdog> <common.md> <farmchains_dir> [--old]

Drives Gate (promote / status / fund / sweep / fees), the signer's policy and feed check, and one
watchdog loop against fake chains. --old runs the same cases against the installed files and only
reports (failures there are what 10b fixes); otherwise any failure exits 1.
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
if len(args) != 5:
    sys.exit(__doc__)
GATE_PATH, SIGNER_PATH, WD_PATH, COMMON_PATH, FC_DIR = args
sys.path.insert(0, FC_DIR)
STUB = os.environ.get("FARMKEYS_STUB")      # local development only; the server uses /opt/farm/lib
if STUB:
    sys.path.insert(0, STUB)
import farmchains  # noqa: E402

RESULTS = []
PRICES = {"ethereum": 2100.0, "base": 2100.0, "arbitrum": 2100.0, "optimism": 2100.0, "bsc": 685.0,
          "polygon": 0.087, "avalanche": 8.29, "hyperevm": 73.7}
USDC = {"base": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913", "bsc": "0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d",
        "polygon": "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359", "hyperevm": "0xb88339CB7199b77E23DB6E890353E22632Ba630f",
        "optimism": "0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85", "avalanche": "0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E"}


def load(path, name):
    loader = importlib.machinery.SourceFileLoader(name, path)
    mod = importlib.util.module_from_spec(importlib.util.spec_from_loader(name, loader))
    loader.exec_module(mod)
    return mod


class Clock:
    def __init__(self):
        self.t = 0.0

    def monotonic(self):
        return self.t

    def sleep(self, s):
        self.t += s


class Stop(BaseException):
    pass


def case(name):
    def deco(fn):
        def run():
            clock = Clock()
            real = (time.monotonic, time.sleep)
            time.monotonic, time.sleep = clock.monotonic, clock.sleep
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
                time.monotonic, time.sleep = real
        run.__name__ = "run"
        return run
    return deco


def fake_priv(label):
    return hashlib.sha256(("farm-test:" + label).encode()).digest()


class FakeChain:
    def __init__(self, fk):
        self.fk = fk
        self.native, self.erc20 = {}, {}
        self.sends, self.calls = {}, []
        self.prices = dict(PRICES)
        self.estimate = 500_000
        self.down = set()

    def call(self, chain, method, params, lane="live"):
        self.calls.append((chain, method))
        if chain in self.down:
            raise RuntimeError("all providers failed")
        if method == "eth_call":
            to, data = params[0]["to"], params[0]["data"]
            if to.lower() == farmchains.ETH_USD_FEED.get(chain, "").lower():
                return hex(int(self.prices[chain] * 1e8))
            if USDC.get(chain) and to.lower() == USDC[chain].lower():
                for (c, a), v in self.erc20.items():
                    if c == chain and data == self.fk.encode_call("balanceOf(address)", a):
                        return hex(v)
                return "0x0"
            raise AssertionError(f"unexpected eth_call to {to} on {chain}")
        if method == "eth_getBalance":
            return hex(self.native.get((chain, params[0]), 0))
        if method == "eth_getTransactionCount":
            return hex(7 + self.sends.get(chain, 0))
        if method == "eth_gasPrice":
            return hex(10**9)
        if method == "eth_maxPriorityFeePerGas":
            return hex(30 * 10**9)
        if method == "eth_estimateGas":
            return hex(self.estimate)
        if method == "eth_sendRawTransaction":
            self.sends[chain] = self.sends.get(chain, 0) + 1
            return "0x" + hashlib.sha256(f"{chain}{self.sends[chain]}".encode()).hexdigest()
        if method == "eth_getTransactionReceipt":
            return {"status": "0x1"}
        raise AssertionError(f"unexpected rpc {method}")


def gate_setup(tmp, chains_cfg=None):
    g_mod = load(GATE_PATH, f"gate_{abs(hash(tmp))}")
    ws, state = os.path.join(tmp, "ws"), os.path.join(tmp, "state")
    for d in (state, f"{ws}/bots/paper", f"{ws}/bots/live", f"{ws}/bots/archive"):
        os.makedirs(d, exist_ok=True)
    g_mod.WS, g_mod.STATE = ws, state
    g_mod.PAPER, g_mod.LIVE, g_mod.ARCHIVE = f"{ws}/bots/paper", f"{ws}/bots/live", f"{ws}/bots/archive"
    g_mod.LOG, g_mod.PNL = f"{state}/gate.log", f"{state}/pnl.json"
    cfg = {"chains": chains_cfg or ["ethereum", "base", "arbitrum", "bsc", "polygon", "avalanche", "optimism", "hyperevm"],
           "max_capital_usd": 2000, "max_daily_loss_usd": 200, "max_loss_per_tx_usd": 50,
           "max_capital_per_bot_usd": 400, "gas_wallet_cap_usd": {"base": 18, "optimism": 18},
           "usdc": dict(USDC), "relay_url": "http://fake"}
    chain = FakeChain(g_mod.farmkeys)
    g = g_mod.Gate.__new__(g_mod.Gate)
    g.cfg, g.rpc, g._price, g.master = cfg, chain, {}, None
    g.key = lambda label, create=False: fake_priv(label)

    class Sub:
        calls = []

        @staticmethod
        def run(a, **kw):
            Sub.calls.append(a)
            if "/opt/farm/bin/gate-root" in a and "adopt" in a:
                bid = a[-1]
                os.rename(f"{g_mod.PAPER}/{bid}", f"{g_mod.LIVE}/{bid}")
                os.makedirs(f"{g_mod.LIVE}/{bid}/state", exist_ok=True)

            class R:
                returncode, stdout, stderr = 0, "", ""
            return R()
    g_mod.subprocess = Sub
    g.wait_receipt = lambda *a, **k: {"status": "0x1"}
    return g_mod, g, chain, Sub


def paper_bot(g_mod, bid, manifest, artifact=None):
    d = f"{g_mod.PAPER}/{bid}"
    os.makedirs(d)
    with open(f"{d}/manifest.yaml", "w") as f:
        f.write(manifest)
    if artifact:
        p = os.path.join(g_mod.WS, "scratch/x/out/E.json")
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w") as f:
            json.dump({"bytecode": {"object": "0x6080604052" + "00" * 40}}, f)


def log_ops(g_mod, op):
    if not os.path.exists(g_mod.LOG):
        return []
    return [r for r in map(json.loads, open(g_mod.LOG)) if r["op"] == op]


BSC_MANIFEST = """id: bscbot
chains: [bsc]
strategy: test
capital_usd: 80
principal_usdc: 50   # USDC principal
allowed_contracts:
  - 0x1111111111111111111111111111111111111111
max_loss_per_tx_usd: 20
"""


@case("gate: promote on bsc sends USDC principal in 18-decimal units (50 USDC = 50e18)")
def t_promote_bsc(tmp):
    g_mod, g, chain, _ = gate_setup(tmp)
    inter = g.intermediate()
    chain.native[("bsc", inter)] = int(1.0 * 1e18)              # 685 USD of BNB
    chain.erc20[("bsc", inter)] = 100 * 10**18
    paper_bot(g_mod, "bscbot", BSC_MANIFEST)
    g.promote("bscbot")
    p = json.load(open(g_mod.PNL))
    assert p["baseline_usdc"]["bscbot"]["bsc"] == 50 * 10**18, p["baseline_usdc"]
    assert log_ops(g_mod, "fund_usdc")[0]["usdc"] == 50 * 10**18


@case("gate: X counts 100 BSC USDC (100e18 raw) as 100 USD, not 1e14 USD")
def t_status_bsc(tmp):
    g_mod, g, chain, _ = gate_setup(tmp)
    chain.erc20[("bsc", g.intermediate())] = 100 * 10**18
    total, detail = g.capital_usd()
    assert abs(detail["intermediate@bsc:usdc"] - 100) < 0.01, detail
    assert total < 2000, total


@case("gate: an implausible native price (ETH-sized reading on polygon) is refused")
def t_price(tmp):
    g_mod, g, chain, _ = gate_setup(tmp)
    chain.prices["polygon"] = 2100.0
    try:
        g.eth_usd("polygon")
    except SystemExit:
        return
    raise AssertionError("price accepted")


@case("gate: fees on polygon take eth_maxPriorityFeePerGas (30 gwei); ethereum/base unchanged")
def t_fees(tmp):
    g_mod, g, chain, _ = gate_setup(tmp)
    mx, tip = g.fees("polygon")
    assert tip >= 30 * 10**9, tip
    chain.calls.clear()
    g.fees("base")
    g.fees("ethereum")
    assert ("base", "eth_maxPriorityFeePerGas") not in chain.calls and \
        ("ethereum", "eth_maxPriorityFeePerGas") not in chain.calls, chain.calls


HYPE_MANIFEST = """id: hypebot
chains:
  - hyperevm
strategy: test
capital_usd: 20
allowed_contracts: [0x2222222222222222222222222222222222222222]
max_loss_per_tx_usd: 20
executor: "scratch/x/out/E.json"
"""


@case("gate: hyperevm promote refused before any funds move when the deploy needs > 2M gas")
def t_hype_gas(tmp):
    g_mod, g, chain, sub = gate_setup(tmp)
    chain.native[("hyperevm", g.intermediate())] = int(5 * 1e18)
    paper_bot(g_mod, "hypebot", HYPE_MANIFEST, artifact=True)
    chain.estimate = 1_900_000                                # x1.2 = 2.28M > 2M
    try:
        g.promote("hypebot")
        raise AssertionError("promoted")
    except SystemExit:
        pass
    assert not chain.sends, chain.sends
    assert not any("adopt" in a for a in sub.calls), sub.calls


@case("gate: hyperevm promote with a small executor deploys it (1.2x gas within 2M)")
def t_hype_ok(tmp):
    g_mod, g, chain, sub = gate_setup(tmp)
    chain.native[("hyperevm", g.intermediate())] = int(5 * 1e18)
    paper_bot(g_mod, "hypebot", HYPE_MANIFEST, artifact=True)
    chain.estimate = 1_000_000
    g.promote("hypebot")
    ex = json.load(open(f"{g_mod.LIVE}/hypebot/state/executor.json"))
    assert "hyperevm" in ex, ex


@case("gate: optimism is capped like base (18 USD of ETH sent out of an 80 USD share)")
def t_op_cap(tmp):
    g_mod, g, chain, _ = gate_setup(tmp)
    chain.native[("optimism", g.intermediate())] = int(0.05 * 1e18)   # 105 USD
    paper_bot(g_mod, "opbot", BSC_MANIFEST.replace("[bsc]", "[optimism]").replace("principal_usdc: 50   # USDC principal\n", "").replace("bscbot", "opbot"))
    g.promote("opbot")
    wei = log_ops(g_mod, "fund")[0]["wei"]
    assert abs(wei / 1e18 * 2100 - 18) < 0.01, wei / 1e18 * 2100


@case("gate: sweep books BSC USDC PnL in 18-decimal units (+2 USDC)")
def t_sweep_bsc(tmp):
    g_mod, g, chain, _ = gate_setup(tmp)
    bid = "bscbot"
    os.makedirs(f"{g_mod.LIVE}/{bid}/state")
    with open(f"{g_mod.LIVE}/{bid}/manifest.yaml", "w") as f:
        f.write(BSC_MANIFEST)
    a = g.addr(f"bot:{bid}")
    chain.erc20[("bsc", a)] = 52 * 10**18
    chain.native[("bsc", a)] = int(0.01 * 1e18)
    g.save_pnl({"day": time.strftime("%Y-%m-%d", time.gmtime()), "realized_usd": {},
                "baseline": {bid: {"bsc": int(0.01 * 1e18)}}, "baseline_usdc": {bid: {"bsc": 50 * 10**18}}})
    g.sweep(bid)
    rec = log_ops(g_mod, "sweep_usdc")[0]
    assert abs(rec["usd"] - 2.0) < 1e-6, rec


def signer_setup():
    s_mod = load(SIGNER_PATH, f"signer_{time.time_ns()}")
    fk = s_mod.farmkeys
    fk.derive_private_key = lambda master, label, create=False: fake_priv(label)   # no master in tests
    chain = FakeChain(fk)
    s = s_mod.Signer.__new__(s_mod.Signer)
    s.cfg = {"max_loss_per_tx_usd": 50, "gas_wallet_cap_usd": {"base": 18, "optimism": 18}, "usdc": dict(USDC)}
    s.master = None
    s.rpc = chain
    s.prices = s_mod.Prices(chain)
    s.prices.disabled = {}
    s.spend = lambda: {"day": "x", "bots": {}}
    s_mod.STATE = tempfile.mkdtemp()
    s_mod.LOG = os.path.join(s_mod.STATE, "signer.log")
    return s_mod, s, chain


def transfer_data(s_mod, dest, amount):
    return s_mod.SEL_TRANSFER + dest[2:].rjust(64, "0") + amount.to_bytes(32, "big").hex()


@case("signer: a 10 USDC transfer on bsc counts 10 USD of spend (not 1e13); 500 USDC exceeds capital")
def t_signer_usdc(tmp):
    s_mod, s, chain = signer_setup()
    m = {"chains": ["bsc"], "allowed_contracts": ["0x1111111111111111111111111111111111111111"], "capital_usd": 400}
    req = {"chain": "bsc", "to": USDC["bsc"], "gas": hex(100_000), "maxFeePerGas": hex(10**9),
           "data": transfer_data(s_mod, "0x1111111111111111111111111111111111111111", 10 * 10**18)}
    why = s.check("b", req, m, "0x" + "ab" * 20)
    assert why is None, why
    req["data"] = transfer_data(s_mod, "0x1111111111111111111111111111111111111111", 500 * 10**18)
    why = s.check("b", req, m, "0x" + "ab" * 20)
    assert why and "capital_usd" in why, why


@case("signer: on base, another chain's USDC address is not an allowed destination")
def t_signer_cross_usdc(tmp):
    s_mod, s, chain = signer_setup()
    m = {"chains": ["base"], "allowed_contracts": ["0x1111111111111111111111111111111111111111"], "capital_usd": 400}
    req = {"chain": "base", "to": USDC["bsc"], "gas": hex(21000), "maxFeePerGas": hex(10**8), "value": hex(10**15)}
    why = s.check("b", req, m, "0x" + "ab" * 20)
    assert why and "allowed_contracts" in why, why


@case("signer: hyperevm refuses gas above 2M; polygon prices POL at 0.087 without 'implausible'")
def t_signer_gas(tmp):
    s_mod, s, chain = signer_setup()
    m = {"chains": ["hyperevm", "polygon"], "allowed_contracts": ["0x1111111111111111111111111111111111111111"], "capital_usd": 400}
    req = {"chain": "hyperevm", "to": "0x1111111111111111111111111111111111111111", "gas": hex(2_500_000), "maxFeePerGas": hex(10**9)}
    why = s.check("b", req, m, "0x" + "ab" * 20)
    assert why and "gas limit" in why, why
    req = {"chain": "polygon", "to": "0x1111111111111111111111111111111111111111", "gas": hex(300_000), "maxFeePerGas": hex(50 * 10**9)}
    why = s.check("b", req, m, "0x" + "ab" * 20)
    assert why is None, why


def desc_hex(text):
    b = text.encode()
    return "0x" + (32).to_bytes(32, "big").hex() + len(b).to_bytes(32, "big").hex() + b.ljust(32, b"\0").hex()


@case("signer: feed check accepts MATIC / USD on polygon; a failing new chain is disabled, a core one stops")
def t_signer_feeds(tmp):
    s_mod, s, chain = signer_setup()
    descs = {c: farmchains.CHAINS[c]["desc"][-1] for c in farmchains.CHAINS}
    fk = s_mod.farmkeys

    def call(c, method, params, lane="live"):
        if c in chain.down:
            raise RuntimeError("down")
        sel = params[0]["data"]
        if sel == fk.selector("decimals()"):
            return hex(8)
        if sel == fk.selector("description()"):
            return desc_hex(descs[c])
        raise AssertionError(sel)
    s.prices.rpc.call = call
    chain.down = {"hyperevm"}
    s.prices.verify_feeds()
    assert set(s.prices.disabled) == {"hyperevm"}, s.prices.disabled
    m = {"chains": ["hyperevm"], "allowed_contracts": ["0x1111111111111111111111111111111111111111"], "capital_usd": 400}
    why = s.check("b", {"chain": "hyperevm", "to": "0x1111111111111111111111111111111111111111", "gas": hex(1), "maxFeePerGas": hex(1)},
                  m, "0x" + "ab" * 20)
    assert why and "disabled" in why, why
    chain.down = {"base"}
    try:
        s.prices.verify_feeds()
        raise AssertionError("signer started with a broken base feed")
    except SystemExit:
        pass


@case("watchdog: an arbitrum/bsc read failure does not hide a 60 USD drop on base in the same loop")
def t_watchdog(tmp):
    wd = load(WD_PATH, f"wd_{time.time_ns()}")
    live = os.path.join(tmp, "live")
    os.makedirs(f"{live}/wbot")
    with open(f"{live}/wbot/manifest.yaml", "w") as f:
        f.write("chains: [arbitrum, bsc, base]\n")
    state = os.path.join(tmp, "state")
    os.makedirs(state)
    conf = os.path.join(tmp, "gate.json")
    json.dump({"relay_url": "x", "watchdog_interval_s": 15, "usdc": dict(USDC), "max_loss_per_tx_usd": 50,
               "max_daily_loss_usd": 200}, open(conf, "w"))
    wd.CONF, wd.LIVE, wd.STATE, wd.INBOX = conf, live, state, os.path.join(tmp, "inbox")
    wd.farmkeys.load_master = lambda: None
    wd.farmkeys.derive_private_key = lambda master, label, create=False: fake_priv(label)
    chain = FakeChain(wd.farmkeys)
    chain.down = {"arbitrum", "bsc"}
    addr = wd.farmkeys.address_of(fake_priv("bot:wbot"))
    chain.native[("base", addr)] = int(0.05 * 1e18)
    wd.rpc = lambda url, c, method, params: chain.call(c, method, params)
    stops = []

    class Sub:
        @staticmethod
        def run(a, **kw):
            if "gate-ctl" in " ".join(a) and "stop" in a:
                stops.append(a)

            class R:
                stdout, returncode = "", 0
            return R()
    wd.subprocess = Sub
    loops = [0]

    def sleep(_):
        loops[0] += 1
        chain.native[("base", addr)] = int(0.05 * 1e18) - int(60 / 2100 * 1e18)     # 60 USD gone
        if loops[0] >= 2:
            raise Stop()
    wd.time.sleep = sleep
    try:
        wd.main()
    except Stop:
        pass
    assert stops, "watchdog did not stop the bot that lost 60 USD on base"


@case("common.md: OP Mainnet under the gas wallet cap, HyperEVM 2M gas, new chains promotable")
def t_common(tmp):
    t = open(COMMON_PATH).read()
    for s in ("OP Stack chains (Base, OP Mainnet)", "2,000,000 gas", "now work like the first three"):
        assert s in t, s
    assert "the gate cannot fund or promote a bot there yet" not in t


for fn in list(globals().values()):
    if callable(fn) and getattr(fn, "__name__", "") == "run":
        fn()

print(f"== {'before 10b (installed files)' if OLD else 'phase 10b'}")
for name, ok, why in RESULTS:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"\n        {why}" if why else ""))
failed = [r for r in RESULTS if not r[1]]
if not OLD:
    print("ALL PASS" if not failed else f"{len(failed)} FAILED")
    sys.exit(1 if failed else 0)
