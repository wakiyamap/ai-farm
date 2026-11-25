#!/usr/bin/env python3
"""Offline tests for phase 15h.  test-15h.py <rpc-relay> [--old]

No network: urllib.request.urlopen is replaced by a fake that answers per provider."""
import importlib.machinery
import importlib.util
import io
import json
import os
import sys
import tempfile
import time
import urllib.error

OLD = "--old" in sys.argv
RELAY = sys.argv[1]
RESULTS = []
ALCH = "alchemy.com"
PUB = "pub.invalid"


def case(name):
    def wrap(fn):
        RESULTS.append((name, fn))
        return fn
    return wrap


def load(path, tmp):
    loader = importlib.machinery.SourceFileLoader("relay15h", path)
    m = importlib.util.module_from_spec(importlib.util.spec_from_loader(loader.name, loader))
    loader.exec_module(m)
    m.DB_PATH = os.path.join(tmp, "ops.db")          # load_today finds no database: nothing restored
    return m


class Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()


def fake(r, script):
    """script: {"alchemy": answer, "public": answer}; answer = dict body, or int HTTP status to raise."""
    calls = []

    def urlopen(req, timeout=None):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        who = "alchemy" if ALCH in url else "public" if PUB in url else url
        calls.append(who)
        ans = script.get(who)
        if ans is None:
            raise AssertionError(f"unexpected upstream call to {who}")
        if isinstance(ans, int):
            raise urllib.error.HTTPError(url, ans, "x", {}, io.BytesIO(b'{"error":"too many"}'))
        return Resp(json.dumps(ans).encode())
    r.urllib.request.urlopen = urlopen
    return calls


def relay(r, historical):
    cfg = {"chains": {"bsc": {"alchemy": "bnb-mainnet", "public": [f"https://{PUB}/bsc"]}},
           "alchemy_daily_cu": {"live": 0, "paper": 900000, "research": 700000, "fork": 600000,
                                "scout": 300000, "watch": 300000},
           "lane_by_user": {"farmfork": "fork", "earner": "scout"}}
    o = r.Relay(cfg, "K")
    o.is_historical = lambda *a: historical
    return o


def names(o, lane, method="eth_getStorageAt", params=("0x1", "0x0", "0x10")):
    return [n for n, _ in o.providers("bsc", lane, method, list(params))]


def cool(o, who, s=10):
    for n, u in o.providers("bsc", "live", "eth_blockNumber", []):
        if n == who:
            o.cooldown[u] = time.monotonic() + s


OKBODY = {"jsonrpc": "2.0", "id": 1, "result": "0x2a"}
TRIE = {"jsonrpc": "2.0", "id": 1, "error": {"code": -32000, "message": "missing trie node abc (path )"}}
RL = {"jsonrpc": "2.0", "id": 1, "error": {"code": -32005, "message": "limit exceeded"}}


@case("fork lane, old state: Alchemy only")
def t_fork_hist(r, tmp):
    assert names(relay(r, True), "fork") == ["alchemy"], names(relay(r, True), "fork")


@case("fork lane, recent state within budget: Alchemy, then public (unchanged)")
def t_fork_recent(r, tmp):
    assert names(relay(r, False), "fork") == ["alchemy", "public"]


@case("research lane, old state: Alchemy, then public (unchanged)")
def t_research_hist(r, tmp):
    assert names(relay(r, True), "research") == ["alchemy", "public"]


@case("fork lane, old state, Alchemy cooling down because of another lane: still asked, public never")
def t_fork_cool(r, tmp):
    o = relay(r, True)
    cool(o, "alchemy", 30)
    calls = fake(r, {"alchemy": OKBODY, "public": TRIE})
    out = o.call("bsc", "fork", "eth_getStorageAt", ["0x1", "0x0", "0x10"], 7)
    assert out.get("result") == "0x2a" and calls == ["alchemy"], (out, calls)


@case("fork lane, old state, Alchemy HTTP 429: error code 429 (anvil retries), public never")
def t_fork_429(r, tmp):
    o = relay(r, True)
    calls = fake(r, {"alchemy": 429, "public": TRIE})
    out = o.call("bsc", "fork", "eth_getStorageAt", ["0x1", "0x0", "0x10"], 7)
    e = out.get("error") or {}
    assert e.get("code") == 429 and "rate limited" in e.get("message", "") and calls == ["alchemy"], (out, calls)


@case("fork lane, old state, Alchemy -32005 in the body: error code 429")
def t_fork_32005(r, tmp):
    o = relay(r, True)
    calls = fake(r, {"alchemy": RL})
    out = o.call("bsc", "fork", "eth_getStorageAt", ["0x1", "0x0", "0x10"], 7)
    assert (out.get("error") or {}).get("code") == 429 and calls == ["alchemy"], (out, calls)


@case("research lane, Alchemy 429 then public: the public answer as before (no 429 rewrite)")
def t_research_429(r, tmp):
    o = relay(r, True)
    calls = fake(r, {"alchemy": 429, "public": TRIE})
    out = o.call("bsc", "research", "eth_getStorageAt", ["0x1", "0x0", "0x10"], 7)
    assert "missing trie node" in (out.get("error") or {}).get("message", "") and calls == ["alchemy", "public"], \
        (out, calls)


@case("send with Alchemy cooling down: still sent to Alchemy")
def t_send_cool(r, tmp):
    o = relay(r, False)
    cool(o, "alchemy", 30)
    calls = fake(r, {"alchemy": {"jsonrpc": "2.0", "id": 1, "result": "0x" + "ab" * 32}})
    out = o.call("bsc", "live", "eth_sendRawTransaction", ["0x02"], 7, allow_send=True)
    assert out.get("result", "").startswith("0xabab") and calls == ["alchemy"], (out, calls)


@case("live lane read with Alchemy cooling down: skipped, public answers (unchanged)")
def t_live_cool(r, tmp):
    o = relay(r, False)
    cool(o, "alchemy", 30)
    calls = fake(r, {"public": OKBODY})
    out = o.call("bsc", "live", "eth_getTransactionCount", ["0x1", "latest"], 7)
    assert out.get("result") == "0x2a" and calls == ["public"], (out, calls)


@case("paper lane with the public node cooling down: skipped, Alchemy answers (unchanged)")
def t_paper_cool(r, tmp):
    o = relay(r, False)
    cool(o, "public", 30)
    calls = fake(r, {"alchemy": OKBODY})
    out = o.call("bsc", "paper", "eth_getTransactionCount", ["0x1", "latest"], 7)
    assert out.get("result") == "0x2a" and calls == ["alchemy"], (out, calls)


def main():
    with tempfile.TemporaryDirectory() as tmp:
        r = load(RELAY, tmp)
        real = r.urllib.request.urlopen
        ok = 0
        for name, fn in RESULTS:
            try:
                fn(r, tmp)
                ok += 1
                print(f"  ok    {name}")
            except Exception as exc:                  # noqa: BLE001
                print(f"  FAIL  {name}: {exc!r}")
            finally:
                r.urllib.request.urlopen = real
        print(f"{ok}/{len(RESULTS)} passed")
        if ok != len(RESULTS) and not OLD:
            sys.exit(1)


if __name__ == "__main__":
    main()
