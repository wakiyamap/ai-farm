#!/usr/bin/env python3
"""Offline tests for phase 15k.  test-15k.py <gate-ctl> <farm-dash> <fix-15k.py> [--old]

gate-ctl is loaded as a module with every chain call replaced by a fake (nothing is signed or sent;
farmkeys is never asked for a key). If /opt/farm/lib is not importable, small stand-ins are used."""
import importlib.machinery
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import types

OLD = "--old" in sys.argv
GATE, DASH, FIX = sys.argv[1:4]
RESULTS = []
BOT = "oneshot-bundles-rebalance-ethereum"


def case(name):
    def wrap(fn):
        RESULTS.append((name, fn))
        return fn
    return wrap


def stubs():
    try:
        sys.path[:0] = ["/opt/farm/pylib", "/opt/farm/lib"]
        import farmchains  # noqa: F401
        import farmkeys    # noqa: F401
        return
    except Exception:                                 # noqa: BLE001 - not on the server: stand-ins
        pass
    fc = types.ModuleType("farmchains")
    fc.CHAIN_IDS = {"ethereum": 1}
    fc.ETH_USD_FEED, fc.CORE = {}, {}
    fc.usdc_scale = lambda chain: 10 ** 6
    fc.price_ok = lambda *a, **k: True
    fc.native = lambda chain: "ETH"
    fc.max_tx_gas = lambda chain: 30_000_000
    fc.feed_chain = lambda chain: chain
    fc.nitro = lambda chain: False
    fc.transfer_gas_budget = lambda chain: 21000
    fc.usdc_gas_budget = lambda chain: 65000
    fk = types.ModuleType("farmkeys")
    sys.modules["farmchains"], sys.modules["farmkeys"] = fc, fk


def load(path, name, tmp):
    loader = importlib.machinery.SourceFileLoader(name, path)
    m = importlib.util.module_from_spec(importlib.util.spec_from_loader(loader.name, loader))
    loader.exec_module(m)
    return m


def gate(tmp, pnl, usdc_raw, wei=int(0.0162 * 1e18), receipt_ok=True):
    stubs()
    g_mod = load(GATE, "gate15k", tmp)
    g_mod.STATE, g_mod.LOG, g_mod.PNL = tmp, os.path.join(tmp, "gate.log"), os.path.join(tmp, "pnl.json")
    g_mod.LIVE = os.path.join(tmp, "live")
    g_mod.CHAIN_IDS = {"ethereum": 1}
    with open(g_mod.PNL, "w") as f:
        json.dump(pnl, f)
    g = g_mod.Gate.__new__(g_mod.Gate)
    g.cfg, g._price = {}, {}
    st = {"usdc": usdc_raw, "wei": wei}
    g.addr = lambda label: "0x" + "b" * 40
    g.intermediate = lambda: "0x" + "c" * 40
    g.fees = lambda chain: (10 ** 9, 10 ** 8)
    g.usdc_raw = lambda chain, a: st["usdc"]
    g.balance_wei = lambda chain, a: st["wei"]
    g.nonce = lambda chain, a, tag="pending": 2

    def send_usdc(chain, label, to, amount, fees=None):
        st["usdc"] = 0
        return "0x" + "1" * 64, None
    g.send_usdc = send_usdc
    g.send_eth = lambda chain, label, to, amount, nonce=None, fees=None, gas=None: ("0x" + "2" * 64, None)
    g.poll_receipt = lambda chain, h, timeout_s=None: {"status": "0x1" if receipt_ok else "0x0"}
    g.transfer_gas = lambda chain, a, b: 21000
    g.eth_usd = lambda chain: 1640.0
    return g_mod, g


def today(g_mod):
    return g_mod.now().strftime("%Y-%m-%d")


def logrecs(g_mod, op):
    with open(g_mod.LOG) as f:
        return [json.loads(x) for x in f if json.loads(x).get("op") == op]


@case("sweep: a bot funded with native only books the USDC it swept back as profit")
def t_native_only(tmp):
    stubs()
    g_mod, _ = gate(tmp, {}, 0)
    pnl = {"day": today(g_mod), "realized_usd": {}, "baseline": {BOT: {"ethereum": 18461958865563704}}, "baseline_usdc": {}}
    g_mod, g = gate(tmp, pnl, 34614241)
    assert g.sweep(BOT) is True
    su = logrecs(g_mod, "sweep_usdc")[-1]
    assert su["usd"] == 34.6142, su
    p = json.load(open(g_mod.PNL))
    native = logrecs(g_mod, "sweep")[-1]["usd"]
    assert abs(p["realized_usd"][BOT] - (34.6142 + native)) < 1e-9 and p["realized_usd"][BOT] > 30, (p, native)
    assert BOT not in p.get("baseline_usdc", {}) and BOT not in p.get("baseline", {}), p


@case("sweep: a bot funded with USDC principal books swept minus principal (unchanged)")
def t_principal(tmp):
    stubs()
    g_mod, _ = gate(tmp, {}, 0)
    pnl = {"day": today(g_mod), "realized_usd": {}, "baseline": {"b2": {"ethereum": int(0.01 * 1e18)}},
           "baseline_usdc": {"b2": {"ethereum": 20_000_000}}}
    g_mod, g = gate(tmp, pnl, 25_000_000)
    g.sweep("b2")
    assert logrecs(g_mod, "sweep_usdc")[-1]["usd"] == 5.0


@case("sweep: a wallet the gate never funded (no baseline at all) books nothing (unchanged)")
def t_unknown(tmp):
    stubs()
    g_mod, _ = gate(tmp, {}, 0)
    pnl = {"day": today(g_mod), "realized_usd": {}, "baseline": {}, "baseline_usdc": {}}
    g_mod, g = gate(tmp, pnl, 3_000_000)
    g.sweep("b3")
    assert logrecs(g_mod, "sweep_usdc")[-1]["usd"] is None
    assert json.load(open(g_mod.PNL))["realized_usd"] == {}


@case("settle_usdc_in_flight: the same rule for a USDC transfer mined late")
def t_inflight(tmp):
    stubs()
    g_mod, g = gate(tmp, {}, 0)
    p = {"day": today(g_mod), "realized_usd": {}, "baseline": {BOT: {"ethereum": 1}}, "baseline_usdc": {},
         "usdc_in_flight": {BOT: {"ethereum": {"txHash": "0x" + "3" * 64, "usdc": 7_500_000, "nonce": 2}}}}
    assert g.settle_usdc_in_flight(p, BOT, "ethereum") == "done"
    assert p["realized_usd"][BOT] == 7.5, p


@case("farm-dash: swept PnL and the 14-day history count sweep_usdc and sweep_usdc_fix")
def t_dash(tmp):
    loader = importlib.machinery.SourceFileLoader("dash15k", DASH)
    d = importlib.util.module_from_spec(importlib.util.spec_from_loader(loader.name, loader))
    loader.exec_module(d)
    d.STATE = tmp
    now = d.dt.datetime.now(d.dt.timezone.utc).isoformat(timespec="seconds")
    with open(os.path.join(tmp, "gate.log"), "w") as f:
        for r in ({"op": "sweep", "usd": -3.7294}, {"op": "sweep_usdc", "usd": None}, {"op": "sweep_usdc_fix", "usd": 34.6142},
                  {"op": "sweep_usdc", "usd": 1.5}, {"op": "fund", "usd": 99}):
            f.write(json.dumps(dict(r, at=now)) + "\n")
    assert d.swept_total() == 32.3848, d.swept_total()
    assert d.pnl_history()[-1][1] == 32.38, d.pnl_history()[-1]


def fix_state(tmp, day):
    log = [{"op": "sweep_usdc", "bot": BOT, "chain": "ethereum", "usdc": 34614241, "usd": None,
            "txHash": "0x100168ae54ab07c12fbde0df9f18589ecb86418ba8b1415da4b1e7a45722561f"},
           {"op": "sweep", "bot": BOT, "usd": -3.7294}]
    with open(os.path.join(tmp, "gate.log"), "w") as f:
        f.write("".join(json.dumps(r) + "\n" for r in log))
    with open(os.path.join(tmp, "pnl.json"), "w") as f:
        json.dump({"day": day, "realized_usd": {"trial-morpho-eth-base": -0.9722, BOT: -3.7294} if day == "2026-11-20" else {},
                   "baseline": {}, "baseline_usdc": {}}, f)


@case("fix-15k: same UTC day -> realized_usd -3.7294 -> +30.8848 and one sweep_usdc_fix record; a rerun changes nothing")
def t_fix(tmp):
    fix_state(tmp, "2026-11-20")
    for _ in range(2):
        subprocess.run([sys.executable, "-I", "-B", FIX, "apply", tmp], check=True, capture_output=True)
    p = json.load(open(os.path.join(tmp, "pnl.json")))
    recs = [json.loads(x) for x in open(os.path.join(tmp, "gate.log"))]
    assert p["realized_usd"][BOT] == 30.8848 and p["realized_usd"]["trial-morpho-eth-base"] == -0.9722, p
    assert [r["op"] for r in recs].count("sweep_usdc_fix") == 1, recs


@case("fix-15k: after the UTC day rolled -> only the gate.log record")
def t_fix_rolled(tmp):
    fix_state(tmp, "2026-11-21")
    subprocess.run([sys.executable, "-I", "-B", FIX, "apply", tmp], check=True, capture_output=True)
    p = json.load(open(os.path.join(tmp, "pnl.json")))
    recs = [json.loads(x) for x in open(os.path.join(tmp, "gate.log"))]
    assert p["realized_usd"] == {} and recs[-1]["op"] == "sweep_usdc_fix", (p, recs[-1])


def main():
    ok = 0
    for name, fn in RESULTS:
        with tempfile.TemporaryDirectory() as tmp:
            try:
                fn(tmp)
                ok += 1
                print(f"  ok    {name}")
            except BaseException as exc:              # noqa: BLE001 - a die() in the old gate is SystemExit
                print(f"  FAIL  {name}: {exc!r}")
    print(f"{ok}/{len(RESULTS)} passed")
    if ok != len(RESULTS) and not OLD:
        sys.exit(1)


if __name__ == "__main__":
    main()
