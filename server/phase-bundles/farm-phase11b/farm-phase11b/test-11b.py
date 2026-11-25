#!/usr/bin/env python3
"""Phase 11b offline tests for farm-dash (no RPC, no systemd, no keys; temp dirs only).

  test-11b.py <farm-dash> [--old]

With --old the failures are only reported (they show what the installed file lacks today).
"""
import contextlib
import datetime as dt
import importlib.machinery
import importlib.util
import io
import json
import os
import sqlite3
import sys
import tempfile
import time

args = [a for a in sys.argv[1:] if a != "--old"]
OLD = "--old" in sys.argv
sys.dont_write_bytecode = True
if len(args) != 1:
    sys.exit(__doc__)
DASH_PATH = args[0]
RESULTS = []
UTC = dt.timezone.utc
TODAY = dt.datetime.now(UTC).strftime("%Y-%m-%d")

GATE = {
    "intermediate": "0x915bd260dCb166f86a499D5fDb3775b5bec70427", "capital_usd": 928.73, "max_capital_usd": 2000,
    "intermediate_balances_usd": {"ethereum": 173.19, "ethereum:usdc": 400.07, "base": 20.42, "base:usdc": 100.0,
                                  "elysium": 0.0, "elysium:usdc": 0.0},
    "daily_loss_usd": 0.0, "max_daily_loss_usd": 200, "frozen": False, "halted": False, "gas_wallet_cap_usd": {"base": 18},
    "live": {"bot-a": {"address": "0xA65AC730fbE06dBb022ae4035132916309c2433A", "service": "ActiveState=active SubState=running",
                       "balances_usd": {"ethereum": 60.0, "ethereum:usdc": 0.0}, "nonces": {"ethereum": 3}},
             "bot-b": {"address": "0xB65AC730fbE06dBb022ae4035132916309c2433A", "service": "ActiveState=inactive SubState=dead",
                       "balances_usd": {"ethereum": 16.0, "ethereum:usdc": 0.0}, "nonces": {"ethereum": 0}}},
}
FEED_OK = {"ok": True, "day": TODAY, "cu_today": 1234, "daily_cu_budget": 700000, "exhausted": False, "heads_offered_on": [],
           "blocked_filters_today": 0, "uptime_s": 7200,
           "chains": {"ethereum": {"status": "up", "connects": 1, "cu_today": 1234, "subscriptions": [
                          {"kind": "logs", "state": "active", "waiters": 1, "idle_s": 2, "cu_today": 1234,
                           "filter": {"address": ["0x" + "11" * 20], "topics": ["0x" + "ab" * 32]}}]},
                      "base": {"status": "idle", "connects": 0, "cu_today": 0, "subscriptions": []}}}
SHOW = ("Id=rpc-relay.service\nLoadState=loaded\nActiveState=active\nSubState=running\n\n"
        "Id=farm-feed.service\nLoadState=loaded\nActiveState=failed\nSubState=failed\n\n"
        "Id=qwen-server.service\nLoadState=not-found\nActiveState=inactive\nSubState=dead\n")
LIST = "fork@base.service loaded active running anvil fork base\nfork@elysium.service loaded failed failed anvil fork elysium\n"


def load(tmp):
    name = f"dash_{time.time_ns()}"
    loader = importlib.machinery.SourceFileLoader(name, DASH_PATH)
    d = importlib.util.module_from_spec(importlib.util.spec_from_loader(name, loader))
    loader.exec_module(d)
    d.WS, d.STATE, d.OPS = f"{tmp}/ws", f"{tmp}/state", f"{tmp}/ops.db"
    d.LEDGER, d.KB = f"{tmp}/ws/ledger.db", f"{tmp}/ws/kb.db"
    d.RELAY, d.FEED = "http://127.0.0.1:9", "http://127.0.0.1:9"          # port 9: nothing answers
    for name_ in ("GATE_CONF", "RUNNERS"):
        if hasattr(d, name_):
            setattr(d, name_, f"{tmp}/{name_.lower()}")
    os.makedirs(d.STATE)
    os.makedirs(f"{d.WS}/decisions/human")
    # what the page read before 11b: empty tables, so only the 11b sources are under test
    con = sqlite3.connect(d.OPS)
    con.execute("CREATE TABLE runs (instance TEXT, started_at TEXT, service_result TEXT, tokens INTEGER, cost_usd REAL)")
    con.commit()
    con.close()
    con = sqlite3.connect(d.KB)
    for t in ("protocols", "actors", "attempts"):
        con.execute(f"CREATE TABLE {t} (id INTEGER)")
    con.execute("CREATE TABLE leads (chain TEXT, target TEXT, status TEXT, updated_at TEXT)")
    con.executemany("INSERT INTO leads VALUES ('ethereum', ?, ?, '2026-11-12')", [("a", "dead_end"), ("b", "dead_end"), ("c", "blocked_infra")])
    con.commit()
    con.close()
    con = sqlite3.connect(d.LEDGER)
    con.execute("CREATE TABLE runs (id INTEGER, started_at TEXT, events INTEGER, cu_seed INTEGER, cu_agent INTEGER)")
    con.execute("CREATE TABLE events (chain TEXT, protocol TEXT, block INTEGER)")
    con.commit()
    con.close()
    d._gate_status = lambda: json.loads(json.dumps(GATE))

    class Sub:
        TimeoutExpired = Exception

        @staticmethod
        def run(a, **kw):
            class R:
                returncode, stderr = 0, ""
                stdout = SHOW if a[:2] == ["systemctl", "show"] and "-p" in a and "Id,LoadState,ActiveState,SubState" in a \
                    else LIST if a[:2] == ["systemctl", "list-units"] and "fork@*.service" in a else ""
            return R()
    d.subprocess = Sub
    return d


def ops_db(d, rows):
    con = sqlite3.connect(d.OPS)
    con.execute("CREATE TABLE rpc_stats (day TEXT, chain TEXT, lane TEXT, provider TEXT, ok INTEGER, failed INTEGER, "
                "refused INTEGER, cu INTEGER, latency_ms INTEGER, cache_hits INTEGER, PRIMARY KEY (day, chain, lane, provider))")
    con.executemany("INSERT INTO rpc_stats VALUES (?,?,?,?,?,?,0,?,?,0)", rows)
    con.commit()
    con.close()


def case(name):
    def deco(fn):
        def run():
            try:
                with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stderr(io.StringIO()), \
                        contextlib.redirect_stdout(io.StringIO()):
                    fn(load(tmp), tmp)
                RESULTS.append((name, True, ""))
            except Exception as exc:                       # noqa: BLE001
                RESULTS.append((name, False, f"{type(exc).__name__}: {exc}"))
        run.__name__ = "run"
        return run
    return deco


@case("Alchemy CU this cycle: sums the relay's Alchemy rows since the cycle began, by lane, and projects the cycle end")
def t_month(d, tmp):
    ops_db(d, [("2026-10-31", "ethereum", "live", "alchemy", 1, 0, 9_000_000, 10),
               ("2026-11-03", "ethereum", "live", "alchemy", 1, 0, 6_000_000, 10),
               ("2026-11-10", "base", "research", "alchemy", 1, 0, 4_000_000, 10),
               ("2026-11-10", "base", "research", "public", 1, 0, 0, 10)])
    m = d.alchemy_month(dt.datetime(2026, 11, 13, 0, 0, tzinfo=UTC))
    assert m["cu"] == 10_000_000 and m["lanes"] == {"live": 6_000_000, "research": 4_000_000}, m
    assert m["since"] == "2026-11-03" and m["ends"] == "2026-12-01", m       # the farm's first day, not the 1st
    assert m["projected_cu"] == 28_000_000, m                               # 1M a day for 10 days, 18 days to go
    assert m["usd"] == 5.3, m


@case("a billing day other than the 1st moves the cycle (ALCHEMY_CYCLE_DAY)")
def t_cycle(d, tmp):
    d.ALCHEMY_CYCLE_DAY = 20
    s, e_ = d.cycle_bounds(dt.datetime(2026, 1, 5, tzinfo=UTC))
    assert (s.strftime("%Y-%m-%d"), e_.strftime("%Y-%m-%d")) == ("2025-12-20", "2026-01-20"), (s, e_)


@case("Alchemy today by chain: one row per chain with the three lanes and the mean latency")
def t_chains(d, tmp):
    ops_db(d, [(TODAY, "ethereum", "live", "alchemy", 90, 10, 5000, 12100),
               (TODAY, "ethereum", "research", "alchemy", 10, 0, 300, 900),
               (TODAY, "elysium", "live", "alchemy", 5, 0, 100, 500),
               (TODAY, "ethereum", "live", "cache", 0, 0, 0, 0)])
    rows = d.rpc_by_chain()
    assert [r["chain"] for r in rows] == ["ethereum", "elysium"], rows
    assert (rows[0]["live"], rows[0]["research"], rows[0]["paper"], rows[0]["avg_ms"]) == (5000, 300, 0, 118), rows[0]


@case("gate log: newest first, the sweep's PnL shown, *_sent records and broken lines skipped")
def t_gate_log(d, tmp):
    recs = [{"op": "promote", "bot": "bot-a", "chains": ["ethereum"], "capital_usd": 16.0, "at": "2026-11-11T22:14:00+00:00", "by": "harness", "role": "paper-reviewer"},
            {"op": "deploy_executor_sent", "bot": "bot-a", "chain": "ethereum", "nonce": 0, "at": "2026-11-11T22:14:30+00:00"},
            {"op": "sweep", "bot": "bot-a", "chain": "ethereum", "wei": 5334139182632984, "usd": -5.0312, "nonce": 1,
             "at": "2026-11-12T17:20:00+00:00", "by": "admin", "role": "?"},
            {"op": "sweep_failed", "bot": "bot-b", "chain": "bsc", "why": "usdc: TimeoutError()", "nonce": 4, "at": "2026-11-12T17:21:00+00:00"},
            {"op": "sweep_usdc", "bot": "bot-b", "chain": "ethereum", "usdc": 80_000_000, "usd": 0.0, "at": "2026-11-12T17:22:00+00:00"}]
    with open(f"{d.STATE}/gate.log", "w") as f:
        f.write("\n".join(json.dumps(r) for r in recs[:2]) + "\n{broken\n" + "\n".join(json.dumps(r) for r in recs[2:]) + "\n")
    rows = d.gate_log_tail()
    assert [r["op"] for r in rows] == ["sweep_usdc", "sweep_failed", "sweep", "promote"], [r["op"] for r in rows]
    assert "PnL -5.0312 USD" in rows[2]["detail"] and "0.005334 native" in rows[2]["detail"] and rows[2]["at"] == "11-13 02:20", rows[2]
    assert "80.00 USDC" in rows[0]["detail"] and "nonce 4" in rows[1]["detail"] and "TimeoutError" in rows[1]["detail"], rows[:2]
    assert rows[3]["by"] == "harness/paper-reviewer", rows[3]


@case("loss since promotion: funded (baseline at the current price) minus the wallet; a bot without a baseline says so")
def t_loss(d, tmp):
    d.native_price = lambda chain, max_age=300: 2000.0
    pnl = {"baseline": {"bot-a": {"ethereum": int(0.05 * 1e18)}}, "baseline_usdc": {"bot-a": {"ethereum": 5_000_000}}}
    out = d.live_loss(GATE, pnl)
    assert out["bot-a"] == {"funded_usd": 105.0, "value_usd": 60.0, "loss_usd": 45.0}, out
    assert out["bot-b"] == {"note": "no baseline"}, out
    d.native_price = lambda chain, max_age=300: None
    assert d.live_loss(GATE, pnl)["bot-a"] == {"note": "price unavailable"}


@case("services: units that do not exist are left out, forks are listed, a failed one is counted")
def t_services(d, tmp):
    sv = d.services()
    assert [s["unit"] for s in sv] == ["rpc-relay", "farm-feed", "fork@base", "fork@elysium"], sv
    tiles = dict((t[0], t) for t in d.extra_tiles({"services": sv, "feed": FEED_OK, "alchemy_month": {"error": "x"}}))
    assert tiles["Services"][1] == "2/4" and tiles["Services"][3] is False and "farm-feed" in tiles["Services"][2], tiles["Services"]


@case("prompt sizes: over 56,000 and over 60,000 are flagged; a prompt.md untouched for a week is left out")
def t_prompts(d, tmp):
    for name, size, age in (("earner-local", 57000, 0), ("meta", 40000, 0), ("paper-reviewer", 61000, 0), ("researcher-chatgpt", 100, 30)):
        os.makedirs(f"{d.RUNNERS}/{name}")
        with open(f"{d.RUNNERS}/{name}/prompt.md", "wb") as f:
            f.write(b"x" * size)
        if age:
            t = time.time() - age * 86400
            os.utime(f"{d.RUNNERS}/{name}/prompt.md", (t, t))
    rows = {r["instance"]: r["state"] for r in d.prompt_sizes()}
    assert rows == {"earner-local": "over 56,000", "meta": "ok", "paper-reviewer": "OVER 60,000: cannot start"}, rows


def full(d, tmp, feed=FEED_OK):
    ops_db(d, [(TODAY, "ethereum", "live", "alchemy", 90, 10, 5000, 12100)])
    with open(f"{d.STATE}/gate.log", "w") as f:
        f.write(json.dumps({"op": "sweep", "bot": "bot-z", "chain": "ethereum", "wei": 1, "usd": -3.7592, "at": TODAY + "T01:00:00+00:00"}) + "\n")
    with open(f"{d.STATE}/pnl.json", "w") as f:
        json.dump({"day": TODAY, "realized_usd": {"bot-z": -3.7592}, "baseline": {"bot-a": {"ethereum": int(0.05 * 1e18)}},
                   "baseline_usdc": {}, "sweep_unsure": {"bot-b": {"ethereum": {"nonce": 1, "wei": 5}}}}, f)
    with open(d.GATE_CONF, "w") as f:
        json.dump({"max_live_loss_usd": 30}, f)
    with open(f"{d.WS}/decisions/human/2026-11-13-next-block-feed.md", "w") as f:
        f.write("x")
    d.native_price = lambda chain, max_age=300: 2000.0
    d.feed_health = lambda: json.loads(json.dumps(feed))
    return d.collect()


@case("page: tiles, intermediate wallet per chain, gate log, feed subscriptions, services and the warnings are on it")
def t_page(d, tmp):
    page = d.render(full(d, tmp))
    for want in ("Alchemy CU this cycle", "Feed CU today", "Intermediate wallet ($693.68)", "elysium", "Gate log (latest 1)",
                 "PnL -3.7592 USD", "40.0 of 30 (funded 100.0)", "1 address(es), topic0 0xabababababababab",
                 "bot-a: 40.0 USD lost since promotion", "live bot bot-b is not running", "bot-b: no baseline in pnl.json",
                 "pnl.json sweep_unsure: bot-b", "farm-feed is failed/failed", "fork@elysium is failed/failed",
                 "2026-11-13-next-block-feed.md", "Alchemy today, by chain"):
        assert want in page, f"missing on the page: {want}"


@case("brief.txt: the same numbers come before '## Paper bots'")
def t_brief(d, tmp):
    b = d.brief(full(d, tmp))
    top = b.split("## Paper bots")[0]
    for want in ("live bot-a: loss since promotion 40.0 of 30 USD (funded 100.0, wallet 60.0) · nonces {\"ethereum\": 3}",
                 "live bot-b: no baseline", "realized today (UTC) {\"bot-z\": -3.7592}",
                 "intermediate wallet: ethereum 173.19 + USDC 400.07 · base 20.42 + USDC 100.0 · zero on: elysium",
                 "alchemy this cycle (", "feed: 1234 of 700000 CU today, exhausted=False, /head on [], 1 subscription(s)",
                 "services: 2/4 active · NOT active: farm-feed failed/failed, fork@elysium failed/failed",
                 "## Needs a look", "## Gate log (newest first, JST)", "sweep bot-z ethereum PnL -3.7592 USD",
                 "## Alchemy today by chain (CU)", "- ethereum: live 5000 paper 0 research 0", "## decisions/human (latest)",
                 "## KB leads by status", "- dead_end 2 · blocked_infra 1"):
        assert want in top, f"missing in the brief: {want}"


@case("with no gate, no feed, no gate.log, no pnl.json and an empty rpc_stats the page and the brief still render")
def t_empty(d, tmp):
    ops_db(d, [])
    d._gate_status = lambda: {"error": "gate: relay down"}
    data = d.collect()
    assert "error" in data["feed"] and data["gate_log"] == [] and data["live_loss"] == {}, data["feed"]
    page, b = d.render(data), d.brief(data)
    assert "farm-feed not answering" in page and "gate unavailable" in page, "page"
    assert "feed: ERROR" in b and "): 0.00M of 95.20M CU, on course for ?" in b, "brief"
    json.dumps(data, default=str)


@case("an exhausted feed and a run-away Alchemy month turn their tiles red")
def t_red(d, tmp):
    feed = dict(FEED_OK, exhausted=True)
    tiles = dict((t[0], t) for t in d.extra_tiles({"services": [], "feed": feed, "alchemy_month": {
        "cu": 60_000_000, "allowance": 95_200_000, "projected_cu": 127_000_000, "usd": 31.8, "since": "a", "ends": "b", "lanes": {}}}))
    assert tiles["Feed CU today"][3] is False and "EXHAUSTED" in tiles["Feed CU today"][2], tiles["Feed CU today"]
    assert tiles["Alchemy CU this cycle"][3] is False and tiles["Alchemy CU this cycle"][1] == "60.00M", tiles["Alchemy CU this cycle"]


@case("10i still holds: the page reuses gate status for 5 minutes, brief.txt asks for 60 s")
def t_cache(d, tmp):
    n, now, real = [0], [1000.0], time.monotonic

    def fake():
        n[0] += 1
        return {"capital_usd": n[0]}
    d._gate_status = fake
    time.monotonic = lambda: now[0]
    try:
        d.collect()
        now[0] += 200
        d.collect()
        assert n[0] == 1, f"gate-ctl status ran {n[0]} times in 200 s"
        now[0] += 90
        d.collect(60)
        assert n[0] == 2, f"gate-ctl status ran {n[0]} times for the brief"
    finally:
        time.monotonic = real


for fn in list(globals().values()):
    if callable(fn) and getattr(fn, "__name__", "") == "run":
        fn()

print(f"== {'before 11b (installed file)' if OLD else 'phase 11b'}")
for name, ok, why in RESULTS:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"\n        {why}" if why else ""))
failed = [r for r in RESULTS if not r[1]]
if not OLD:
    print("ALL PASS" if not failed else f"{len(failed)} FAILED")
    sys.exit(1 if failed else 0)
