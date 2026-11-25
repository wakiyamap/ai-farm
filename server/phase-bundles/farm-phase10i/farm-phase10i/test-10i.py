#!/usr/bin/env python3
"""Phase 10i offline tests: what the watchdog reads per round, and the dashboard's gate cache
(no RPC, no keys, temp dirs only).

  test-10i.py <farm-watchdog> <farm-dash> <farmchains_dir> [--old]

With --old the failures are only reported (they show what the installed files do today).
"""
import contextlib
import hashlib
import importlib.machinery
import importlib.util
import inspect
import io
import json
import os
import sys
import tempfile
import time

args = [a for a in sys.argv[1:] if a != "--old"]
OLD = "--old" in sys.argv
sys.dont_write_bytecode = True
if len(args) != 3:
    sys.exit(__doc__)
WD_PATH, DASH_PATH, FC_DIR = args
sys.path.insert(0, FC_DIR)
STUB = os.environ.get("FARMKEYS_STUB")      # local development only; the server uses /opt/farm/lib
if STUB:
    sys.path.insert(0, STUB)
import farmchains  # noqa: E402

RESULTS = []
PRICE = 2000.0
USDC = {"ethereum": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48", "base": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"}
CU = {"eth_getBalance": 20, "eth_getTransactionCount": 20, "eth_call": 26}


def eth(usd):
    return int(usd / PRICE * 1e18)


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


def run_loop(tmp, bots, rounds, balance_interval=60, step=None, signer_log=(), pnl_data=None, fail=None):
    """bots: {id: (chains, {chain: [wei, usdc_raw, nonce]})}. step(round, state) changes them before
    round `round` (1-based for the rounds after the first). fail(round, bot, chain, method) -> True
    makes that read raise. Returns (calls per round, stops, state)."""
    wd = load(WD_PATH, "wd")
    live, state = os.path.join(tmp, "live"), os.path.join(tmp, "state")
    os.makedirs(state)
    for b, (chains, _) in bots.items():
        os.makedirs(f"{live}/{b}")
        with open(f"{live}/{b}/manifest.yaml", "w") as f:
            f.write(f"chains: [{', '.join(chains)}]\n")
    if pnl_data is not None:
        with open(f"{state}/pnl.json", "w") as f:
            json.dump(pnl_data, f)
    with open(f"{state}/signer.log", "w") as f:
        for r in signer_log:
            f.write(json.dumps(r) + "\n")
    open(f"{state}/gate.log", "w").close()
    cfg = {"relay_url": "x", "watchdog_interval_s": 15, "usdc": dict(USDC), "max_loss_per_tx_usd": 50,
           "max_daily_loss_usd": 200, "max_live_loss_usd": 30}
    if balance_interval is not None:
        cfg["watchdog_balance_interval_s"] = balance_interval
    conf = os.path.join(tmp, "gate.json")
    with open(conf, "w") as f:
        json.dump(cfg, f)
    wd.CONF, wd.LIVE, wd.STATE, wd.INBOX = conf, live, state, os.path.join(tmp, "inbox")
    fk = wd.farmkeys
    fk.load_master = lambda: None
    fk.derive_private_key = lambda master, label, create=False: fake_priv(label)
    addr = {b: fk.address_of(fake_priv(f"bot:{b}")) for b in bots}
    st = {(b, c): list(v) for b, (_, vs) in bots.items() for c, v in vs.items()}
    rnd = [0]
    calls = [[]]

    def rpc(url, chain, method, params):
        who = next((b for b, a in addr.items() if a in json.dumps(params)), None)
        kind = method
        if method == "eth_call":
            to = params[0]["to"].lower()
            if to == farmchains.ETH_USD_FEED[chain].lower():
                kind = "price"
            else:
                who = next(b for b, a in addr.items() if params[0]["data"] == fk.encode_call("balanceOf(address)", a))
                kind = "usdc"
        calls[-1].append((kind, who, chain))
        if fail and fail(rnd[0], who, chain, kind):
            raise RuntimeError("all providers failed")
        if kind == "eth_getBalance":
            return hex(st[(who, chain)][0])
        if kind == "eth_getTransactionCount":
            return hex(st[(who, chain)][2])
        if kind == "price":
            return hex(int(PRICE * 1e8))
        return hex(st[(who, chain)][1])
    wd.rpc = rpc
    stops = []

    class Sub:
        @staticmethod
        def run(a, **kw):
            if "/opt/farm/bin/gate-ctl" in a and "stop" in a:
                stops.append((rnd[0], a[-1]))

            class R:
                stdout, returncode = "", 0
            return R()
    wd.subprocess = Sub

    def sleep(_):
        rnd[0] += 1
        if rnd[0] >= rounds:
            raise Stop()
        calls.append([])
        if step:
            step(rnd[0], st)
    wd.time.sleep = sleep
    try:
        wd.main()
    except Stop:
        pass
    return calls, stops, st


def cu(calls):
    return sum(CU["eth_call"] if k in ("price", "usdc") else CU[k] for rc in calls for k, _, _ in rc)


TWO = {"bot-a": (["ethereum"], {"ethereum": [eth(100), 0, 1]}),
       "bot-b": (["ethereum"], {"ethereum": [eth(100), 0, 1]})}


@case("with watchdog_balance_interval_s 60: nonces every round, balances and USDC every 4th, one price read per round that needs it")
def t_reads(tmp):
    calls, stops, _ = run_loop(tmp, TWO, 8)
    kinds = [sorted(k for k, _, _ in rc) for rc in calls]
    nonce_only = ["eth_getTransactionCount"] * 2
    full = sorted(nonce_only + ["eth_getBalance"] * 2 + ["usdc"] * 2 + ["price"])
    assert kinds[0] == full and kinds[4] == full, f"round 0: {kinds[0]}, round 4: {kinds[4]}"
    for i in (1, 2, 3, 5, 6, 7):
        assert kinds[i] == nonce_only, f"round {i} read {kinds[i]}"
    assert not stops, stops


@case("the Alchemy cost of 8 quiet rounds with two bots falls from 1,472 CU to under 600")
def t_cost(tmp):
    calls, _, _ = run_loop(tmp, TWO, 8)
    assert cu(calls) < 600, f"{cu(calls)} CU"


@case("without the gate.json key the watchdog reads balances every round, as before")
def t_default(tmp):
    calls, _, _ = run_loop(tmp, TWO, 3, balance_interval=None)
    for i, rc in enumerate(calls):
        assert sum(1 for k, _, _ in rc if k == "eth_getBalance") == 2, f"round {i}: {rc}"


@case("a 60 USD drop without a transaction of the bot (USDC pulled by a spender) stops it at the next balance read")
def t_drop_no_nonce(tmp):
    bots = {"bot-a": (["ethereum"], {"ethereum": [eth(20), 100_000_000, 1]})}

    def step(r, st):
        if r == 1:
            st[("bot-a", "ethereum")][1] = 40_000_000
    calls, stops, _ = run_loop(tmp, bots, 6, step=step)
    assert stops == [(4, "bot-a")], f"stops (round, bot): {stops}"


@case("a 60 USD drop that comes with a transaction of the bot stops it in the same round")
def t_drop_with_nonce(tmp):
    bots = {"bot-a": (["ethereum"], {"ethereum": [eth(100), 0, 1]})}

    def step(r, st):
        if r == 1:
            st[("bot-a", "ethereum")][0] = eth(40)
            st[("bot-a", "ethereum")][2] = 2
    log = [{"bot": "bot-a", "decision": "sent", "chain": "ethereum", "nonce": 1}]
    calls, stops, _ = run_loop(tmp, bots, 3, step=step, signer_log=log)
    assert stops == [(1, "bot-a")], f"stops (round, bot): {stops}"


@case("a nonce found in no log halts everything in the round it appears, balance round or not")
def t_unknown_nonce(tmp):
    bots = {"bot-a": (["ethereum"], {"ethereum": [eth(100), 0, 1]})}

    def step(r, st):
        if r == 2:
            st[("bot-a", "ethereum")][2] = 2
    calls, stops, _ = run_loop(tmp, bots, 4, step=step)
    assert stops and stops[0] == (2, "--all"), f"stops (round, target): {stops}"


@case("the live-loss stop still fires: funded 100 USD, wallet worth 60 USD")
def t_live_loss(tmp):
    bots = {"bot-a": (["ethereum"], {"ethereum": [eth(60), 0, 1]})}
    pnl = {"day": "x", "realized_usd": {}, "baseline": {"bot-a": {"ethereum": eth(100)}}, "baseline_usdc": {}}
    calls, stops, _ = run_loop(tmp, bots, 2, pnl_data=pnl)
    assert stops and stops[0] == (0, "bot-a"), f"stops (round, bot): {stops}"


@case("the live-loss stop judges a later loss at the next balance read, not from stale values")
def t_live_loss_later(tmp):
    bots = {"bot-a": (["ethereum"], {"ethereum": [eth(20), 80_000_000, 1]})}
    pnl = {"day": "x", "realized_usd": {}, "baseline": {"bot-a": {"ethereum": eth(20)}},
           "baseline_usdc": {"bot-a": {"ethereum": 80_000_000}}}

    def step(r, st):
        if r == 2:
            st[("bot-a", "ethereum")][1] = 45_000_000      # 35 USD gone: over the 30 USD stop, under L
    calls, stops, _ = run_loop(tmp, bots, 6, step=step, pnl_data=pnl)
    assert stops == [(4, "bot-a")], f"stops (round, bot): {stops}"


@case("a balance read that fails is tried again in the next round, not four rounds later")
def t_retry(tmp):
    bots = {"bot-a": (["ethereum"], {"ethereum": [eth(100), 0, 1]})}
    calls, _, _ = run_loop(tmp, bots, 3, fail=lambda r, b, c, k: r == 0 and k == "eth_getBalance")
    assert any(k == "eth_getBalance" for k, _, _ in calls[1]), f"round 1 read {calls[1]}"
    assert not any(k == "eth_getBalance" for k, _, _ in calls[2]), f"round 2 read {calls[2]}"


@case("a bot on two chains: both chains are read, the price once per feed")
def t_two_chains(tmp):
    bots = {"bot-a": (["ethereum", "base"], {"ethereum": [eth(50), 0, 1], "base": [eth(10), 0, 1]})}
    calls, stops, _ = run_loop(tmp, bots, 2)
    prices = [c for k, _, c in calls[0] if k == "price"]
    assert sorted(prices) == ["base", "ethereum"], prices
    assert not stops, stops


# --- dashboard --------------------------------------------------------------------------------

def dash_with_clock():
    d = load(DASH_PATH, "dash")
    now = [1000.0]
    n = [0]

    def fake():
        n[0] += 1
        return {"capital_usd": n[0]}
    d._gate_status = fake
    return d, now, n


@case("dashboard: the page reuses gate status for 5 minutes")
def t_dash_page(tmp):
    d, now, n = dash_with_clock()
    real = time.monotonic
    time.monotonic = lambda: now[0]
    try:
        d.gate_status()
        now[0] += 200
        d.gate_status()
        assert n[0] == 1, f"gate-ctl status ran {n[0]} times in 200 s"
        now[0] += 150
        d.gate_status()
        assert n[0] == 2, f"gate-ctl status ran {n[0]} times in 350 s"
    finally:
        time.monotonic = real


@case("dashboard: brief.txt asks for gate data at most 60 s old")
def t_dash_brief(tmp):
    d, now, n = dash_with_clock()
    real = time.monotonic
    time.monotonic = lambda: now[0]
    try:
        d.gate_status()
        now[0] += 90
        v = d.gate_status(60)
        assert n[0] == 2 and v == {"capital_usd": 2}, f"runs {n[0]}, value {v}"
    finally:
        time.monotonic = real
    src = inspect.getsource(d.H.do_GET)
    assert 'collect(60 if self.path.startswith("/brief.txt") else 300)' in src, "do_GET does not pass the age"
    assert "gate_status(gate_max_age)" in inspect.getsource(d.collect), "collect() does not pass the age"


for fn in list(globals().values()):
    if callable(fn) and getattr(fn, "__name__", "") == "run":
        fn()

print(f"== {'before 10i (installed files)' if OLD else 'phase 10i'}")
for name, ok, why in RESULTS:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"\n        {why}" if why else ""))
failed = [r for r in RESULTS if not r[1]]
if not OLD:
    print("ALL PASS" if not failed else f"{len(failed)} FAILED")
    sys.exit(1 if failed else 0)
