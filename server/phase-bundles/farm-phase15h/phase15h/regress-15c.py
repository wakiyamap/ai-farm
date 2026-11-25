#!/usr/bin/env python3
"""Offline tests for phase 15c. Nothing is sent anywhere.

  test-15c.py <rpc-relay> <farm-hermes> [--old]
"""
import datetime as dt
import importlib.machinery
import importlib.util
import json
import os
import pwd
import sqlite3
import sys
import tempfile

OLD = "--old" in sys.argv
RELAY, HERMES = sys.argv[1], sys.argv[2]
RESULTS = []


def case(name):
    def wrap(fn):
        RESULTS.append((name, fn))
        return fn
    return wrap


def load(path, name):
    loader = importlib.machinery.SourceFileLoader(name, path)
    m = importlib.util.module_from_spec(importlib.util.spec_from_loader(loader.name, loader))
    loader.exec_module(m)
    return m


def relay_obj(r, spent=0, budget=None):
    o = r.Relay.__new__(r.Relay)
    o.chains = {"base": {"alchemy": "base-mainnet", "public": ["https://pub.invalid"]}}
    o.key = "KEY"
    o.budget = budget or {"live": 1, "paper": 1, "research": 700000, "fork": 400000, "scout": 300000}
    o.private_send = {}
    o.lane_by_user = {"farmfork": "fork", "earner": "scout"}

    class S:
        def alchemy_cu_today(self, lane):
            return spent
    o.stats = S()
    o.is_historical = lambda *a: False
    return o


def provs(r, o, lane):
    try:
        p = o.providers("base", lane, "eth_getStorageAt", ["0x0", "0x0", "0x10"])
    except TypeError:
        p = o.providers("base", lane, "eth_getStorageAt", ["0x0", "0x0", "0x10"], None)
    return [n for n, _ in p]


@case("lanes: fork and scout exist")
def t_lanes(r, h, tmp):
    assert "fork" in r.LANES and "scout" in r.LANES


@case("fork lane: Alchemy first within its budget, public only once it is spent")
def t_fork(r, h, tmp):
    assert provs(r, relay_obj(r, spent=10), "fork") == ["alchemy", "public"]
    assert provs(r, relay_obj(r, spent=400000), "fork") == ["public"]


@case("scout and research lanes: public first, Alchemy as fallback within the budget")
def t_scout(r, h, tmp):
    assert provs(r, relay_obj(r, spent=10), "scout") == ["public", "alchemy"]
    assert provs(r, relay_obj(r, spent=300000), "scout") == ["public"]
    assert provs(r, relay_obj(r, spent=10), "research") == ["public", "alchemy"]


@case("lane mapping: farmfork -> fork, earner -> scout whatever they ask; others cannot ask for fork/scout")
def t_map(r, h, tmp):
    u = {"farmfork": "fork", "earner": "scout"}
    assert r.mapped_lane("farmfork", "research", u) == "fork"
    assert r.mapped_lane("earner", "research", u) == "scout"
    assert r.mapped_lane("earner", "live", u) == "scout"
    assert r.mapped_lane("harness", "research", u) == "research"
    assert r.mapped_lane("harness", "fork", u) == "research"
    assert r.mapped_lane("farmbot", "scout", u) == "research"
    assert r.mapped_lane("farmbot", "paper", u) == "paper"
    assert r.mapped_lane(None, "live", u) == "live"


@case("peer_user: finds the client's socket row in /proc/net/tcp")
def t_peer(r, h, tmp):
    me = os.getuid()
    p = os.path.join(tmp, "tcp")
    with open(p, "w") as f:
        f.write("  sl  local_address rem_address   st tx_queue rx_queue tr tm->when retrnsmt   uid  timeout inode\n")
        f.write("   0: 0100007F:2161 0100007F:D431 01 00000000:00000000 00:00000000 00000000  999 0 1 1\n")   # server side
        f.write(f"   1: 0100007F:D431 0100007F:2161 01 00000000:00000000 00:00000000 00000000 {me:>5} 0 2 1\n")
    assert r.peer_user(("127.0.0.1", 0xD431), 8545, (p,)) == pwd.getpwuid(me).pw_name
    assert r.peer_user(("127.0.0.1", 1234), 8545, (p,)) is None


@case("cycle_from_db: projection and the 85% alert")
def t_cycle(r, h, tmp):
    db = os.path.join(tmp, "ops.db")
    con = sqlite3.connect(db)
    con.execute("CREATE TABLE rpc_stats (day TEXT, chain TEXT, lane TEXT, provider TEXT, ok INT, failed INT, "
                "refused INT, cu INT, latency_ms INT, cache_hits INT)")
    for d in range(3, 18):
        con.execute("INSERT INTO rpc_stats VALUES (?,?,?,?,0,0,0,?,0,0)", (f"2026-11-{d:02d}", "base", "live", "alchemy", 4_000_000))
    con.commit()
    con.close()
    now = dt.datetime(2026, 11, 18, 0, 0, tzinfo=dt.timezone.utc)
    c = r.cycle_from_db(db, 95_200_000, 1, now)
    assert c["cu"] == 60_000_000 and c["since"] == "2026-11-03" and c["ends"] == "2026-12-01", c
    assert c["projected_cu"] == 112_000_000 and c["alert_85"] is True, c
    c2 = r.cycle_from_db(db, 200_000_000, 1, now)
    assert c2["alert_85"] is False


@case("farm-hermes: Bearer header, stream refused, other paths refused")
def t_hermes(r, h, tmp):
    api = h.HermesApi({"upstream": "https://example.invalid/hermes",
                       "allow": {"GET": ["/v2/updates/price", "/v2/price_feeds"]},
                       "deny": ["/v2/updates/price/stream"]}, "SECRET")
    assert api.allowed("GET", "/v2/updates/price/latest")
    assert not api.allowed("GET", "/v2/updates/price/stream")
    assert not api.allowed("POST", "/v2/updates/price/latest")
    assert not api.allowed("GET", "/v2/../admin")
    assert api.auth_headers() == {"Authorization": "Bearer SECRET"}
    assert api.scrub("x SECRET y") == "x *** y"


def main():
    with tempfile.TemporaryDirectory() as tmp:
        r = load(RELAY, "relay15c")
        try:
            h = load(HERMES, "hermes15c")
        except Exception:                             # noqa: BLE001
            h = None
        ok = 0
        for name, fn in RESULTS:
            try:
                fn(r, h, tmp)
                ok += 1
                print(f"  ok    {name}")
            except Exception as exc:                  # noqa: BLE001
                print(f"  FAIL  {name}: {exc!r}")
        print(f"{ok}/{len(RESULTS)} passed")
        if ok != len(RESULTS) and not OLD:
            sys.exit(1)


if __name__ == "__main__":
    main()
