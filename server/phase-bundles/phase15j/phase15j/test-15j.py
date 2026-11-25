#!/usr/bin/env python3
"""Offline tests for phase 15j.  test-15j.py <farm-dash> [--old]

Loads farm-dash as a module (nothing listens, nothing is read from the network); STATE and the
day file point at a temporary directory."""
import datetime as dt
import importlib.machinery
import importlib.util
import json
import os
import sys
import tempfile

OLD = "--old" in sys.argv
DASH = sys.argv[1]
RESULTS = []
UTC = dt.timezone.utc


def case(name):
    def wrap(fn):
        RESULTS.append((name, fn))
        return fn
    return wrap


def load(tmp):
    loader = importlib.machinery.SourceFileLoader("dash15j", DASH)
    m = importlib.util.module_from_spec(importlib.util.spec_from_loader(loader.name, loader))
    loader.exec_module(m)
    m.STATE = tmp
    m.DAY_FILE = os.path.join(tmp, "dash-pnl-day.json")
    return m


def T(h, day=20):
    return dt.datetime(2026, 11, day, h, 0, tzinfo=UTC)


@case("live_pnl: the sign of loss since promotion, bots without a number left out")
def t_live_pnl(m, tmp):
    ll = {"a": {"loss_usd": -1.64}, "b": {"loss_usd": 0.03}, "c": {"note": "no baseline"}}
    assert m.live_pnl(ll) == {"a": 1.64, "b": -0.03}, m.live_pnl(ll)


@case("pnl_today: snapshot at the first call of the day, then the change since it")
def t_today(m, tmp):
    r = m.pnl_today({"a": 1.00, "b": -0.03}, T(0))
    assert r["by_bot"] == {"a": 0.0, "b": 0.0} and r["since"] == "00:00 UTC", r
    r = m.pnl_today({"a": 1.64, "b": -0.05}, T(6))
    assert r["by_bot"] == {"a": 0.64, "b": -0.02} and r["total"] == 0.62, r


@case("pnl_today: a bot promoted after the snapshot starts at 0 (its deploy gas counts today)")
def t_new_bot(m, tmp):
    m.pnl_today({"a": 1.0}, T(0))
    r = m.pnl_today({"a": 1.0, "new": -0.04}, T(5))
    assert r["by_bot"]["new"] == -0.04 and r["by_bot"]["a"] == 0.0, r


@case("pnl_today: the next UTC day closes the previous day's total into history (14 days kept)")
def t_rollover(m, tmp):
    m.pnl_today({"a": 0.0}, T(0, 19))
    m.pnl_today({"a": 0.50}, T(23, 19))
    r = m.pnl_today({"a": 0.70}, T(0, 20))
    assert r["history"] == {"2026-11-19": 0.5} and r["by_bot"] == {"a": 0.0}, r
    s = json.load(open(m.DAY_FILE))
    s["history"] = {f"2026-10-{d:02d}": 1.0 for d in range(1, 20)}
    json.dump(s, open(m.DAY_FILE, "w"))
    r = m.pnl_today({"a": 0.70}, T(0, 21))
    assert len(r["history"]) == 14 and "2026-11-20" in r["history"], r["history"]


@case("pnl_today: a broken day file is replaced, not fatal")
def t_broken(m, tmp):
    with open(m.DAY_FILE, "w") as f:
        f.write("{broken")
    r = m.pnl_today({"a": 2.0}, T(3))
    assert r["by_bot"] == {"a": 0.0} and r["since"] == "03:00 UTC", r


@case("swept_total: the sum of gate.log sweep records only")
def t_swept(m, tmp):
    with open(os.path.join(tmp, "gate.log"), "w") as f:
        for r in ({"op": "sweep", "usd": -5.0312}, {"op": "promote", "usd": 9}, {"op": "sweep", "usd": 1.5}):
            f.write(json.dumps(r) + "\n")
        f.write("{broken\n")
    assert m.swept_total() == -3.5312, m.swept_total()


def data(m, tmp):
    lp = {"trial-peapods-arb-arbitrum": 1.64, "trial-aave-arbitrum": -0.02}
    m.pnl_today({"trial-peapods-arb-arbitrum": 1.0, "trial-aave-arbitrum": -0.02}, T(0))
    today = m.pnl_today(lp, T(1))
    live = {b: {"service": "ActiveState=active SubState=running", "address": "0x" + "1" * 40,
                "balances_usd": {"arbitrum": 10.0}, "nonces": {"arbitrum": 3}} for b in lp}
    return {
        "now": "2026-11-20 08:00 JST (23:00 UTC)",
        "gate": {"capital_usd": 1, "max_capital_usd": 2, "daily_loss_usd": 0, "max_daily_loss_usd": 200,
                 "frozen": False, "halted": False, "live": live, "intermediate_balances_usd": {"arbitrum": 3.0}},
        "relay": {"alchemy_cu_today": {"live": 1}}, "agents": [], "paper": [], "timers": [], "runs": [], "rpc": [],
        "ledger": [], "ledger_runs": [], "kb": {}, "leads": [], "sessions": [],
        "inbox_human": [], "inbox_meta": [], "inbox_live": [], "pnl": [("2026-11-19", 0.0), ("2026-11-20", -0.01)],
        "feed": {"error": "x"}, "alchemy_month": {"error": "x"}, "rpc_chains": [], "services": [], "gate_log": [],
        "realized_today": {"trial-aave-base": -0.0073}, "sweep_pending": {},
        "live_loss": {b: {"loss_usd": -v, "funded_usd": 10, "value_usd": 10 + v} for b, v in lp.items()},
        "live_pnl": lp, "live_pnl_today": today, "swept_total": -0.0073, "max_live_loss_usd": 30,
        "prompts": [], "decisions": [], "lead_counts": [],
    }


@case("brief: summary line, the bots in profit, pnl today per bot, swept today")
def t_brief(m, tmp):
    b = m.brief(data(m, tmp))
    assert "live PnL since promotion +1.62 USD (gains +1.64, losses -0.02) · today (UTC, since 00:00 UTC) +0.64" in b, b[:1500]
    assert "in profit: trial-peapods-arb-arbitrum +1.64" in b and "swept all time -0.0073" in b, b[:1500]
    assert "pnl today +0.64" in b and 'swept today (UTC, gate realized_usd) {"trial-aave-base": -0.0073}' in b, b[:1500]
    assert "realized today (UTC)" not in b


@case("page: Live PnL tile, PnL columns in the live table, swept PnL title, live PnL by day")
def t_page(m, tmp):
    p = m.render(data(m, tmp))
    for want in ("Live PnL", "+1.62", "today +0.64 · gains +1.64 / losses -0.02", "pnl_since_promote_usd", "pnl_today_usd",
                 "swept_today_usd", "Swept PnL of stopped bots", "Live PnL by UTC day"):
        assert want in p, f"missing on the page: {want}"
    assert "realized_today_usd" not in p


@case("collect-time extras: live PnL is built from live_loss without the network")
def t_extras(m, tmp):
    m.gate_status = lambda max_age=300: {"live": {"x": {"balances_usd": {"base": 5.5}}}}
    m.pnl_state = lambda: {"baseline": {"x": {"base": int(0.002 * 1e18)}}, "realized_usd": {}}
    m.native_price = lambda chain, max_age=300: 2500.0
    for name in ("feed_health", "alchemy_month", "rpc_by_chain", "services", "gate_log_tail", "prompt_sizes", "decisions"):
        setattr(m, name, lambda *a, **k: [])
    m.q = lambda *a, **k: []
    with open(os.path.join(tmp, "gate.log"), "w") as f:
        f.write("")
    x = m.extras()
    assert x["live_pnl"] == {"x": 0.5} and x["live_pnl_today"]["by_bot"] == {"x": 0.0} and x["swept_total"] == 0.0, x


def main():
    ok = 0
    for name, fn in RESULTS:
        with tempfile.TemporaryDirectory() as tmp:
            try:
                fn(load(tmp), tmp)
                ok += 1
                print(f"  ok    {name}")
            except Exception as exc:                  # noqa: BLE001
                print(f"  FAIL  {name}: {exc!r}")
    print(f"{ok}/{len(RESULTS)} passed")
    if ok != len(RESULTS) and not OLD:
        sys.exit(1)


if __name__ == "__main__":
    main()
