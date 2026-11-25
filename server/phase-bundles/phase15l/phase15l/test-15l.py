#!/usr/bin/env python3
"""Offline tests for phase 15l.  test-15l.py <farm-dash> [--old]

Loads farm-dash as a module (nothing listens, no gate-ctl, no network); STATE and WS point at a
temporary directory and `gate-ctl status` is replaced by a counter."""
import importlib.machinery
import importlib.util
import os
import sys
import tempfile
import time

OLD = "--old" in sys.argv
DASH = sys.argv[1]
RESULTS = []


def case(name):
    def wrap(fn):
        RESULTS.append((name, fn))
        return fn
    return wrap


def load(tmp):
    loader = importlib.machinery.SourceFileLoader("dash15l", DASH)
    m = importlib.util.module_from_spec(importlib.util.spec_from_loader(loader.name, loader))
    loader.exec_module(m)
    m.STATE = os.path.join(tmp, "state")
    m.WS = os.path.join(tmp, "ws")
    os.makedirs(m.STATE)
    os.makedirs(os.path.join(m.WS, "bots", "live"))
    m.DAY_FILE = os.path.join(m.STATE, "dash-pnl-day.json")
    calls = []

    def fake_status():
        calls.append(1)
        return {"live": {"b%d" % len(calls): {}}}
    m._gate_status = fake_status
    m._gate_cache.update(t=0, v=None)
    return m, calls


def append_log(m, line):
    with open(os.path.join(m.STATE, "gate.log"), "a", encoding="utf-8") as f:
        f.write(line + "\n")


@case("gate_status: cached while gate.log is unchanged (no extra gate-ctl status)")
def t_cached(m, calls, tmp):
    append_log(m, '{"op":"promote"}')
    m.gate_status(300)
    m.gate_status(300)
    m.gate_status(300)
    assert len(calls) == 1, calls


@case("gate_status: a new gate.log record (stop / promote) drops the cache at once")
def t_invalidate(m, calls, tmp):
    append_log(m, '{"op":"promote"}')
    a = m.gate_status(300)
    time.sleep(0.01)
    append_log(m, '{"op":"stop"}')
    b = m.gate_status(300)
    assert len(calls) == 2 and a != b, (calls, a, b)
    m.gate_status(300)
    assert len(calls) == 2, calls


@case("gate_status: no gate.log -> the plain 5-minute cache, as before")
def t_nolog(m, calls, tmp):
    m.gate_status(300)
    m.gate_status(300)
    assert len(calls) == 1, calls


@case("live_loss: a bot stopped since the cached status (no baseline, no live dir) is not reported")
def t_stopped(m, calls, tmp):
    g = {"live": {"gone": {"balances_usd": {}}}}
    assert m.live_loss(g, {"baseline": {}}) == {}, m.live_loss(g, {"baseline": {}})


@case("live_loss: a running bot without a baseline is still reported")
def t_live_nobase(m, calls, tmp):
    os.makedirs(os.path.join(m.WS, "bots", "live", "here"))
    g = {"live": {"here": {"balances_usd": {}}}}
    assert m.live_loss(g, {"baseline": {}}) == {"here": {"note": "no baseline"}}


@case("warnings: the stopped bot gives no 'no baseline' line")
def t_warn(m, calls, tmp):
    g = {"live": {"gone": {"balances_usd": {}, "service": "ActiveState=active"}}}
    d = {"gate": g, "live_loss": m.live_loss(g, {"baseline": {}}), "max_live_loss_usd": 30}
    assert not any("no baseline" in w for w in m.warnings(d)), m.warnings(d)


ok = 0
for name, fn in RESULTS:
    with tempfile.TemporaryDirectory() as tmp:
        try:
            m, calls = load(tmp)
            fn(m, calls, tmp)
            ok += 1
            print(f"  PASS  {name}")
        except Exception as exc:          # noqa: BLE001
            print(f"  FAIL  {name}\n        {type(exc).__name__}: {exc}")
print(f"{ok} of {len(RESULTS)} pass" if OLD else ("ALL PASS" if ok == len(RESULTS) else f"{len(RESULTS) - ok} FAILED"))
sys.exit(0 if OLD or ok == len(RESULTS) else 1)
