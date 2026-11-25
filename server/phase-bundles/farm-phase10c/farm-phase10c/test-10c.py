#!/usr/bin/env python3
"""Phase 10c offline tests: the watchdog's live-loss stop (no RPC, no keys, temp dirs only).

  test-10c.py <farm-watchdog> <common.md> <farmchains_dir> [--old]

Runs the watchdog's main loop for a few rounds against a fake chain. --old reports only.
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
if len(args) != 3:
    sys.exit(__doc__)
WD_PATH, COMMON_PATH, FC_DIR = args
sys.path.insert(0, FC_DIR)
STUB = os.environ.get("FARMKEYS_STUB")      # local development only; the server uses /opt/farm/lib
if STUB:
    sys.path.insert(0, STUB)
import farmchains  # noqa: E402

RESULTS = []
PRICE = {"ethereum": 2000.0, "base": 2000.0, "arbitrum": 2000.0, "bsc": 700.0}
USDC = {"base": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913", "bsc": "0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d"}


class Stop(BaseException):
    pass


def load(path):
    name = f"wd_{time.time_ns()}"
    loader = importlib.machinery.SourceFileLoader(name, path)
    mod = importlib.util.module_from_spec(importlib.util.spec_from_loader(name, loader))
    loader.exec_module(mod)
    return mod


def fake_priv(label):
    return hashlib.sha256(("farm-test:" + label).encode()).digest()


def case(name):
    def deco(fn):
        def run():
            real_sleep = time.sleep
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
                time.sleep = real_sleep
        run.__name__ = "run"
        return run
    return deco


def run_loop(tmp, bots, pnl, rounds, step, down=()):
    """bots: {id: (chains, {chain: (wei, usdc_raw)})}; step(round, balances) mutates balances."""
    wd = load(WD_PATH)
    live, state = os.path.join(tmp, "live"), os.path.join(tmp, "state")
    os.makedirs(state)
    for b, (chains, _) in bots.items():
        os.makedirs(f"{live}/{b}")
        with open(f"{live}/{b}/manifest.yaml", "w") as f:
            f.write(f"chains: [{', '.join(chains)}]\n")
    with open(f"{state}/pnl.json", "w") as f:
        json.dump(pnl, f)
    conf = os.path.join(tmp, "gate.json")
    with open(conf, "w") as f:
        json.dump({"relay_url": "x", "watchdog_interval_s": 15, "usdc": USDC, "max_loss_per_tx_usd": 50,
                   "max_daily_loss_usd": 200, "max_live_loss_usd": 30}, f)
    wd.CONF, wd.LIVE, wd.STATE, wd.INBOX = conf, live, state, os.path.join(tmp, "inbox")
    fk = wd.farmkeys
    fk.load_master = lambda: None
    fk.derive_private_key = lambda master, label, create=False: fake_priv(label)
    addr = {b: fk.address_of(fake_priv(f"bot:{b}")) for b in bots}
    bal = {(b, c): list(v) for b, (_, vs) in bots.items() for c, v in vs.items()}

    def rpc(url, chain, method, params):
        if chain in down:
            raise RuntimeError("all providers failed")
        who = next((b for b, a in addr.items() if a in json.dumps(params)), None)
        if method == "eth_getBalance":
            return hex(bal[(who, chain)][0])
        if method == "eth_getTransactionCount":
            return hex(3)
        if method == "eth_call":
            to = params[0]["to"].lower()
            if to == farmchains.ETH_USD_FEED[chain].lower():
                return hex(int(PRICE[chain] * 1e8))
            if to == USDC.get(chain, "").lower():
                b = next(b for b, a in addr.items() if params[0]["data"] == fk.encode_call("balanceOf(address)", a))
                return hex(bal[(b, chain)][1])
        raise AssertionError(f"unexpected {method} {params}")
    wd.rpc = rpc
    stops = []

    class Sub:
        @staticmethod
        def run(a, **kw):
            if "gate-ctl" in " ".join(a) and "stop" in a:
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
        step(n[0], bal)
    wd.time.sleep = sleep
    try:
        wd.main()
    except Stop:
        pass
    wakes = os.listdir(wd.INBOX) if os.path.isdir(wd.INBOX) else []
    return stops, wakes


def wei(usd, chain="ethereum"):
    return int(usd / PRICE[chain] * 1e18)


@case("live-loss stop: 10 USD lost per round (each under L=50) stops the bot once the total passes 30")
def t_cumulative(tmp):
    def step(r, bal):
        bal[("b1", "ethereum")][0] -= wei(10)
    stops, wakes = run_loop(tmp, {"b1": (["ethereum"], {"ethereum": (wei(100), 0)})},
                            {"baseline": {"b1": {"ethereum": wei(100)}}}, rounds=6, step=step)
    assert stops == ["b1"], stops
    assert wakes, "live-operator not woken"


@case("live-loss stop: a bot in profit or within 30 USD is left alone")
def t_ok(tmp):
    def step(r, bal):
        bal[("b1", "ethereum")][0] -= wei(5)          # 25 USD after 5 rounds
        bal[("b2", "ethereum")][0] += wei(20)
    stops, _ = run_loop(tmp, {"b1": (["ethereum"], {"ethereum": (wei(100), 0)}),
                              "b2": (["ethereum"], {"ethereum": (wei(50), 0)})},
                        {"baseline": {"b1": {"ethereum": wei(100)}, "b2": {"ethereum": wei(50)}}}, rounds=6, step=step)
    assert stops == [], stops


@case("live-loss stop: BSC USDC counted in 18 decimals (50 -> 15 USDC = 35 USD lost) stops the bot")
def t_bsc_usdc(tmp):
    def step(r, bal):
        bal[("b1", "bsc")][1] = 15 * 10**18 if r >= 2 else 40 * 10**18
    stops, _ = run_loop(tmp, {"b1": (["bsc"], {"bsc": (wei(5, "bsc"), 50 * 10**18)})},
                        {"baseline": {"b1": {"bsc": wei(5, "bsc")}}, "baseline_usdc": {"b1": {"bsc": 50 * 10**18}}},
                        rounds=4, step=step)
    assert stops == ["b1"], stops


@case("live-loss stop: no baseline in pnl.json -> no stop; an unreadable chain -> no judgement that round")
def t_guard(tmp):
    def step(r, bal):
        bal[("b1", "base")][0] -= wei(10, "base")
        bal[("b2", "base")][0] -= wei(10, "base")
    stops, _ = run_loop(tmp, {"b1": (["base"], {"base": (wei(100, "base"), 0)}),
                              "b2": (["arbitrum", "base"], {"arbitrum": (0, 0), "base": (wei(100, "base"), 0)})},
                        {"baseline": {"b2": {"base": wei(100, "base")}}}, rounds=6, step=step, down=("arbitrum",))
    assert stops == [], stops


@case("common.md: the live-loss stop is a hard constraint enforced by the watchdog")
def t_common(tmp):
    t = open(COMMON_PATH).read()
    assert "- **Live-loss stop**: the watchdog stops" in t


for fn in list(globals().values()):
    if callable(fn) and getattr(fn, "__name__", "") == "run":
        fn()

print(f"== {'before 10c (installed files)' if OLD else 'phase 10c'}")
for name, ok, why in RESULTS:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"\n        {why}" if why else ""))
failed = [r for r in RESULTS if not r[1]]
if not OLD:
    print("ALL PASS" if not failed else f"{len(failed)} FAILED")
    sys.exit(1 if failed else 0)
