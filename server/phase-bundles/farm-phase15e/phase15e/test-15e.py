#!/usr/bin/env python3
"""Offline tests for phase 15e.  test-15e.py <rpc-relay> <farm-watchdog> [--old]"""
import datetime as dt
import importlib.machinery
import importlib.util
import os
import sqlite3
import sys
import tempfile

OLD = "--old" in sys.argv
RELAY, WD = sys.argv[1], sys.argv[2]
RESULTS = []


def case(name):
    def wrap(fn):
        RESULTS.append((name, fn))
        return fn
    return wrap


def load(path):
    loader = importlib.machinery.SourceFileLoader("relay15e", path)
    m = importlib.util.module_from_spec(importlib.util.spec_from_loader(loader.name, loader))
    loader.exec_module(m)
    return m


def db_with(tmp, rows):
    db = os.path.join(tmp, f"ops{len(rows)}.db")
    con = sqlite3.connect(db)
    con.execute("CREATE TABLE rpc_stats (day TEXT, chain TEXT, lane TEXT, provider TEXT, ok INT, failed INT, "
                "refused INT, cu INT, latency_ms INT, cache_hits INT)")
    for day, cu in rows:
        con.execute("INSERT INTO rpc_stats VALUES (?,?,?,?,0,0,0,?,0,0)", (day, "base", "live", "alchemy", cu))
    con.commit()
    con.close()
    return db


@case("lane watch exists")
def t_lane(r, tmp):
    assert "watch" in r.LANES and "watch" not in r.MAPPED_ONLY


@case("watch lane: public first, Alchemy within its budget")
def t_watch(r, tmp):
    o = r.Relay.__new__(r.Relay)
    o.chains = {"base": {"alchemy": "base-mainnet", "public": ["https://pub.invalid"]}}
    o.key, o.budget, o.private_send = "K", {"watch": 300000}, {}

    class S:
        def __init__(self, n):
            self.n = n

        def alchemy_cu_today(self, lane):
            return self.n
    o.is_historical = lambda *a: False
    o.stats = S(10)
    assert [n for n, _ in o.providers("base", "watch", "eth_getTransactionCount", ["0x0", "latest"])] == ["public", "alchemy"]
    o.stats = S(300000)
    assert [n for n, _ in o.providers("base", "watch", "eth_getTransactionCount", ["0x0", "latest"])] == ["public"]


@case("cycle: a steady month projects as before")
def t_steady(r, tmp):
    db = db_with(tmp, [(f"2026-11-{d:02d}", 4_000_000) for d in range(3, 18)])
    c = r.cycle_from_db(db, 95_200_000, 1, dt.datetime(2026, 11, 18, 0, 0, tzinfo=dt.timezone.utc))
    assert c["projected_cu"] == 112_000_000 and c["projected_cu_recent"] == 112_000_000, c


@case("cycle: a jump today raises the projection and the alert")
def t_jump(r, tmp):
    rows = [(f"2026-11-{d:02d}", 2_000_000) for d in range(3, 18)] + [("2026-11-18", 1_500_000)]
    db = db_with(tmp, rows)
    now = dt.datetime(2026, 11, 18, 6, 0, tzinfo=dt.timezone.utc)      # a quarter of the day: 6M/day pace
    c = r.cycle_from_db(db, 95_200_000, 1, now)
    assert c["pace_cu_per_day"] == 6_000_000, c
    assert c["projected_cu"] < 70_000_000 and c["projected_cu_recent"] > 100_000_000 and c["alert_85"], c


@case("farm-watchdog reads through lane watch")
def t_wd(r, tmp):
    src = open(WD, encoding="utf-8").read()
    assert '?lane=watch"' in src and '?lane=live"' not in src


def main():
    with tempfile.TemporaryDirectory() as tmp:
        r = load(RELAY)
        ok = 0
        for name, fn in RESULTS:
            try:
                fn(r, tmp)
                ok += 1
                print(f"  ok    {name}")
            except Exception as exc:                  # noqa: BLE001
                print(f"  FAIL  {name}: {exc!r}")
        print(f"{ok}/{len(RESULTS)} passed")
        if ok != len(RESULTS) and not OLD:
            sys.exit(1)


if __name__ == "__main__":
    main()
