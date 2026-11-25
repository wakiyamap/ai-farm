#!/usr/bin/env python3
"""Offline tests for phase 15i.  test-15i.py <rpc-relay> <context/earner> <context/builder> [--old]

No network: urllib.request.urlopen is replaced by a fake. The context scripts run on copies whose
/srv/farm/ws and kb paths point at a temporary workspace and a fake kb that prints the query.
Also re-checks the 15h / 15c / 15e relay behaviour that 15i keeps (other lanes, sends, cooldown, 429)."""
import importlib.machinery
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.error

OLD = "--old" in sys.argv
RELAY, EARNER, BUILDER = sys.argv[1:4]
RESULTS = []
ALCH, PUB = "alchemy.com", "pub.invalid"


def case(name):
    def wrap(fn):
        RESULTS.append((name, fn))
        return fn
    return wrap


def load(path, tmp):
    loader = importlib.machinery.SourceFileLoader("relay15i", path)
    m = importlib.util.module_from_spec(importlib.util.spec_from_loader(loader.name, loader))
    loader.exec_module(m)
    m.DB_PATH = os.path.join(tmp, "ops.db")
    return m


class Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()


def fake(r, script):
    calls = []

    def urlopen(req, timeout=None):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        who = "alchemy" if ALCH in url else "public" if PUB in url else url
        calls.append(who)
        ans = script.get(who)
        if ans is None:
            raise AssertionError(f"unexpected upstream call to {who}")
        if isinstance(ans, int):
            raise urllib.error.HTTPError(url, ans, "x", {}, io.BytesIO(b'{"error":"x"}'))
        return Resp(json.dumps(ans).encode())
    r.urllib.request.urlopen = urlopen
    return calls


def relay(r, historical=False, spent=None):
    cfg = {"chains": {"bsc": {"alchemy": "bnb-mainnet", "public": [f"https://{PUB}/bsc"]}},
           "alchemy_daily_cu": {"live": 0, "paper": 900000, "research": 1500000, "fork": 95200000,
                                "scout": 1200000, "watch": 300000},
           "lane_by_user": {"farmfork": "fork", "earner": "scout"}}
    o = r.Relay(cfg, "K")
    o.is_historical = lambda *a: historical
    if spent is not None:
        o.stats.alchemy_cu_today = lambda lane: spent
    return o


def names(o, lane, method="eth_getStorageAt", params=("0x1", "0x0", "0x10")):
    return [n for n, _ in o.providers("bsc", lane, method, list(params))]


def cool(o, who, s=30):
    for n, u in o.providers("bsc", "live", "eth_blockNumber", []):
        if n == who:
            o.cooldown[u] = time.monotonic() + s


OK = {"jsonrpc": "2.0", "id": 1, "result": "0x2a"}
TRIE = {"jsonrpc": "2.0", "id": 1, "error": {"code": -32000, "message": "missing trie node abc"}}
RL = {"jsonrpc": "2.0", "id": 1, "error": {"code": -32005, "message": "limit exceeded"}}
P = ["0x1", "0x0", "0x10"]


# ---- 15i: fork lane ---------------------------------------------------------------------------

@case("fork lane: Alchemy only even when is_historical() says no (anvil's reads)")
def t_fork_recent(r, tmp):
    assert names(relay(r, False), "fork") == ["alchemy"], names(relay(r, False), "fork")


@case("fork lane: Alchemy only past any daily spend (no cap)")
def t_fork_spent(r, tmp):
    o = relay(r, False, spent=10**9)
    for m, p in (("eth_getStorageAt", P), ("eth_getBalance", ["0x1", {"blockHash": "0x" + "1" * 64}]),
                 ("eth_getBlockByNumber", ["0x10", False]), ("eth_chainId", []), ("eth_getProof", ["0x1", [], "0x10"])):
        assert names(o, "fork", m, p) == ["alchemy"], (m, names(o, "fork", m, p))


@case("fork lane, Alchemy cooling down after another lane: still asked, public never")
def t_fork_cool(r, tmp):
    o = relay(r, False, spent=10**9)
    cool(o, "alchemy")
    calls = fake(r, {"alchemy": OK, "public": TRIE})
    out = o.call("bsc", "fork", "eth_getStorageAt", P, 7)
    assert out.get("result") == "0x2a" and calls == ["alchemy"], (out, calls)


@case("fork lane, Alchemy HTTP 429 / -32005: error code 429 (anvil retries), public never")
def t_fork_429(r, tmp):
    for ans in (429, RL):
        o = relay(r, False)
        calls = fake(r, {"alchemy": ans, "public": TRIE})
        out = o.call("bsc", "fork", "eth_getStorageAt", P, 7)
        assert (out.get("error") or {}).get("code") == 429 and calls == ["alchemy"], (ans, out, calls)


@case("fork lane, Alchemy HTTP 403: the Alchemy error, public never")
def t_fork_403(r, tmp):
    o = relay(r, False)
    calls = fake(r, {"alchemy": 403, "public": OK})
    out = o.call("bsc", "fork", "eth_getStorageAt", P, 7)
    assert "alchemy: HTTP 403" in (out.get("error") or {}).get("message", "") and calls == ["alchemy"], (out, calls)


# ---- kept from 15c / 15e / 15h ----------------------------------------------------------------

@case("research and scout: public first, Alchemy within the budget, public only past it (15c)")
def t_research(r, tmp):
    assert names(relay(r, False, spent=10), "research") == ["public", "alchemy"]
    assert names(relay(r, False, spent=10), "scout") == ["public", "alchemy"]
    assert names(relay(r, False, spent=1200000), "scout") == ["public"]
    assert names(relay(r, False, spent=1499999), "research") == ["public", "alchemy"]


@case("research, old state: Alchemy, then public (15h, unchanged)")
def t_research_hist(r, tmp):
    assert names(relay(r, True), "research") == ["alchemy", "public"]


@case("research lane, Alchemy 429 then public: the public answer, no 429 rewrite (15h)")
def t_research_429(r, tmp):
    o = relay(r, True)
    calls = fake(r, {"alchemy": 429, "public": TRIE})
    out = o.call("bsc", "research", "eth_getStorageAt", P, 7)
    assert "missing trie node" in (out.get("error") or {}).get("message", "") and calls == ["alchemy", "public"], (out, calls)


@case("watch lane: public first, Alchemy within its budget (15e)")
def t_watch(r, tmp):
    assert names(relay(r, False, spent=10), "watch", "eth_getTransactionCount", ["0x0", "latest"]) == ["public", "alchemy"]
    assert names(relay(r, False, spent=300000), "watch", "eth_getTransactionCount", ["0x0", "latest"]) == ["public"]


@case("live lane read: Alchemy then public; cooling Alchemy is skipped (unchanged)")
def t_live(r, tmp):
    o = relay(r, False)
    assert names(o, "live") == ["alchemy", "public"]
    cool(o, "alchemy")
    calls = fake(r, {"public": OK})
    out = o.call("bsc", "live", "eth_getTransactionCount", ["0x1", "latest"], 7)
    assert out.get("result") == "0x2a" and calls == ["public"], (out, calls)


@case("send with Alchemy cooling down: still sent to Alchemy only (15h)")
def t_send(r, tmp):
    o = relay(r, False)
    cool(o, "alchemy")
    calls = fake(r, {"alchemy": {"jsonrpc": "2.0", "id": 1, "result": "0x" + "ab" * 32}})
    out = o.call("bsc", "live", "eth_sendRawTransaction", ["0x02"], 7, allow_send=True)
    assert out.get("result", "").startswith("0xabab") and calls == ["alchemy"], (out, calls)


@case("lane mapping: farmfork -> fork, earner -> scout; nobody can ask for fork (15c)")
def t_map(r, tmp):
    u = {"farmfork": "fork", "earner": "scout"}
    assert r.mapped_lane("farmfork", "research", u) == "fork"
    assert r.mapped_lane("earner", "live", u) == "scout"
    assert r.mapped_lane("harness", "fork", u) == "research"


# ---- context scripts --------------------------------------------------------------------------

def workspace(tmp):
    ws = os.path.join(tmp, "ws")
    bin_ = os.path.join(tmp, "bin")
    os.makedirs(bin_, exist_ok=True)
    with open(os.path.join(bin_, "kb"), "w") as f:
        f.write('#!/bin/sh\necho "KB: $*"\n')
    os.chmod(os.path.join(bin_, "kb"), 0o755)

    def bot(kind, bid, review=None, manifest="strategy: x\n", newer=False):
        d = os.path.join(ws, "bots", kind, bid)
        os.makedirs(os.path.join(d, "logs"), exist_ok=True)
        with open(os.path.join(d, "manifest.yaml"), "w") as f:
            f.write(manifest)
        with open(os.path.join(d, "bot.py"), "w") as f:
            f.write("pass\n")
        old = time.time() - 3600
        os.utime(os.path.join(d, "manifest.yaml"), (old, old))
        os.utime(os.path.join(d, "bot.py"), (old, old))
        if review is not None:
            with open(os.path.join(d, "review.md"), "w") as f:
                f.write(review)
            os.utime(os.path.join(d, "review.md"), (old + 60, old + 60))
        if newer:
            os.utime(os.path.join(d, "bot.py"), None)
        with open(os.path.join(d, "logs", "bot.jsonl"), "w") as f:      # runtime logs never count
            f.write("{}\n")
    bot("paper", "bold-fix", "# Review\n\n**Decision: fix** (cheap-chain trial review).\n")
    bot("paper", "heading-fix", "unchanged since abc, decision fix stands (2026-11-19).\n\n"
        "## 2026-11-19 09:52 UTC — fix (cheap-chain trial)\n")
    bot("paper", "parked", "**Decision: wait (parked: approved, waiting for a live trial slot)**\n\n"
        "An earlier review said fix; the builder fixed it.\n")
    bot("paper", "old-wait-heading", "## 2026-11-19 01:59 UTC — wait (parked: approved)\n\n"
        "**Decision:** approved.\n\n## 2026-11-18 — fix\n")
    bot("paper", "resubmitted", "**Decision: fix**\n", newer=True)
    bot("paper", "with-lead", "**Decision: wait**\n", manifest="strategy: x\nlead: 301\n")
    bot("live", "trial-a", manifest="lead_id: 297\nnotes: see leads:303\n")
    bot("live", "trial-b")
    return ws, bin_


def run_ctx(path, tmp, ws, bin_, arg):
    src = open(path, encoding="utf-8").read().replace("/srv/farm/ws", ws) \
        .replace("KB=/opt/farm/bin/kb", f"KB={bin_}/kb").replace("export PATH=/opt/farm/bin:$PATH", f"export PATH={bin_}:$PATH")
    p = os.path.join(tmp, os.path.basename(path) + ".sh")
    with open(p, "w") as f:
        f.write(src)
    return subprocess.run(["bash", p, arg], capture_output=True, text=True, timeout=60).stdout


def section(out, title):
    lines = out.split("\n")
    i = next(k for k, l in enumerate(lines) if l.startswith(title))
    body = []
    for l in lines[i + 1:]:
        if l.startswith("### "):
            break
        body.append(l)
    return "\n".join(body)


@case("context: the fix list reads the first decision line or heading; parked and old headings are not fix")
def t_fix(r, tmp):
    ws, bin_ = workspace(tmp)
    out = run_ctx(EARNER, tmp, ws, bin_, "builder-claude")
    fix = section(out, "### Paper bots waiting for a fix")
    assert "- bold-fix:" in fix and "- heading-fix:" in fix, fix
    for b in ("parked", "old-wait-heading", "resubmitted", "with-lead"):
        assert f"- {b}:" not in fix, (b, fix)


@case("context: a bot changed after its fix review is listed as resubmitted, not as builder work")
def t_resub(r, tmp):
    ws, bin_ = workspace(tmp)
    out = run_ctx(EARNER, tmp, ws, bin_, "builder-claude")
    rs = section(out, "### Paper bots resubmitted")
    assert "- resubmitted: bot.py is newer than review.md" in rs and "bold-fix" not in rs, rs


@case("context: measured leads leave out TRIAL BOT PLACED / NOT A BUILD TARGET and leads with a bot")
def t_measured(r, tmp):
    ws, bin_ = workspace(tmp)
    out = run_ctx(EARNER, tmp, ws, bin_, "builder-claude")
    q = section(out, "### Measured leads without a bot")
    assert "NOT LIKE '%TRIAL BOT PLACED%'" in q and "NOT LIKE '%NOT A BUILD TARGET%'" in q, q
    assert "id NOT IN (297,301,303)" in q, q


@case("context: builder shows the trial count against 45")
def t_builder(r, tmp):
    ws, bin_ = workspace(tmp)
    src = open(BUILDER, encoding="utf-8").read().replace("/opt/farm/context/earner", EARNER)
    p = os.path.join(tmp, "builder.sh")
    with open(p, "w") as f:
        f.write(src.replace("/srv/farm/ws", ws).replace("export PATH=/opt/farm/bin:$PATH", f"export PATH={bin_}:$PATH"))
    out = subprocess.run(["bash", p, "builder"], capture_output=True, text=True, timeout=60).stdout
    assert "### Trial bots live: 2 / 45" in out, out[-400:]


def main():
    with tempfile.TemporaryDirectory() as tmp:
        r = load(RELAY, tmp)
        real = r.urllib.request.urlopen
        ok = 0
        for name, fn in RESULTS:
            sub = tempfile.mkdtemp(dir=tmp)
            try:
                fn(r, sub)
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
