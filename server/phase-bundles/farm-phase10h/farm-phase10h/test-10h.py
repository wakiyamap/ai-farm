#!/usr/bin/env python3
"""Phase 10h offline tests for ledger-ingest (no RPC, in-memory SQLite only).

  test-10h.py <ledger-ingest> [--old]

With --old the failures are only reported (they show what the installed file does today).
"""
import importlib.machinery
import importlib.util
import sqlite3
import sys

args = [a for a in sys.argv[1:] if a != "--old"]
OLD = "--old" in sys.argv
sys.dont_write_bytecode = True
if len(args) != 1:
    sys.exit(__doc__)

loader = importlib.machinery.SourceFileLoader("ledger_ingest_under_test", args[0])
spec = importlib.util.spec_from_loader(loader.name, loader)
li = importlib.util.module_from_spec(spec)
loader.exec_module(li)

CU = {"eth_getLogs": 60, "eth_blockNumber": 10, "eth_getCode": 20, "eth_getTransactionReceipt": 20}
TOPIC = "0x" + "ab" * 32
RESULTS = []


def addr(i):
    return "0x" + f"{i:040x}"


def case(name):
    def deco(fn):
        def run():
            try:
                fn()
                RESULTS.append((name, True, ""))
            except AssertionError as exc:
                RESULTS.append((name, False, str(exc) or "assertion failed"))
            except Exception as exc:                       # noqa: BLE001
                RESULTS.append((name, False, f"{type(exc).__name__}: {exc}"))
        return run
    return deco


class FakeRpc:
    """Counts CU like the real Rpc. logs: list of (chain, block, log_index, emitter)."""

    def __init__(self, logs=(), no_code=(), fail_for=(), max_range=None):
        self.cu = 0
        self.logs, self.no_code, self.fail_for, self.max_range = list(logs), set(no_code), set(fail_for), max_range
        self.calls = []

    def call(self, chain, method, params):
        self.cu += CU.get(method, 30)
        self.calls.append((chain, method, params))
        if method == "eth_getCode":
            return "0x" if params[0] in self.no_code else "0x6080"
        if method == "eth_getTransactionReceipt":
            return {"from": "0x" + "ee" * 20}
        if method == "eth_getLogs":
            f = params[0]
            lo, hi = int(f["fromBlock"], 16), int(f["toBlock"], 16)
            want = f["address"] if isinstance(f["address"], list) else [f["address"]]
            if self.fail_for & set(want):
                raise RuntimeError(f"{chain} eth_getLogs: upstream timeout")
            if self.max_range and hi - lo + 1 > self.max_range:
                raise RuntimeError(f"{chain} eth_getLogs: block range too large")
            return [{"transactionHash": "0x" + f"{b:060x}" + f"{i:04x}", "blockNumber": hex(b), "logIndex": hex(i),
                     "address": e, "topics": [TOPIC, "0x" + "00" * 12 + "cc" * 20], "data": "0x"}
                    for (c, b, i, e) in self.logs if c == chain and lo <= b <= hi and e in want]
        raise AssertionError(f"unexpected {method}")

    def getlogs(self):
        return [c for c in self.calls if c[1] == "eth_getLogs"]


def db():
    con = sqlite3.connect(":memory:")
    con.executescript(li.SCHEMA)
    return con


def source(chains, actor="who"):
    return {"id": "src.test", "protocol": "proto", "kind": "kind", "chains": chains, "event": "E(address)",
            "topic0": TOPIC, "indexed": ["who"], "data": [], "actor_field": actor, "_types": ["address"]}


CFG = {"confirmations": 2, "blocks_per_call": {"ethereum": 1000, "arbitrum": 10000},
       "backfill_days": 7, "block_time_s": {"ethereum": 12, "arbitrum": 0.25}}


def run_ticks(con, s, n, share=600, rpc_factory=FakeRpc, head0=26_000_000, arb0=400_000_000, **kw):
    """n timer runs, 15 minutes apart, each with a fresh CU count and `share` CU for this source."""
    last = None
    for t in range(n):
        rpc = rpc_factory(**kw)
        heads = {"ethereum": head0 + 75 * t, "arbitrum": arb0 + 3600 * t}
        li.ingest_source(con, rpc, CFG, s, heads, share, {"unverified": [], "errors": []})
        last = (rpc, heads)
    return last


def cursors(con, chain="ethereum"):
    return dict(con.execute("SELECT contract, next_block FROM cursors WHERE chain=? AND verified=1", (chain,)).fetchall())


@case("a source with 20 emitters gets all 20 initialized and to the head on the 600 CU share")
def t_all_emitters():
    con, s = db(), source({"ethereum": [addr(i) for i in range(1, 21)]})
    rpc, heads = run_ticks(con, s, 60)
    cur = cursors(con)
    assert len(cur) == 20, f"only {len(cur)} of 20 emitters have a cursor after 60 runs"
    head = heads["ethereum"] - CFG["confirmations"]
    late = [a for a, n in cur.items() if n <= head]
    assert not late, f"{len(late)} emitters are still behind the head after 60 runs"


@case("the second chain of a source is reached (20 ethereum + 20 arbitrum emitters)")
def t_second_chain():
    con = db()
    s = source({"ethereum": [addr(i) for i in range(1, 21)], "arbitrum": [addr(i) for i in range(101, 121)]})
    run_ticks(con, s, 400)
    eth, arb = cursors(con, "ethereum"), cursors(con, "arbitrum")
    assert len(eth) == 20, f"ethereum: {len(eth)} of 20 cursors"
    assert len(arb) == 20, f"arbitrum: {len(arb)} of 20 cursors after 400 runs"


@case("at the head, one run costs one eth_getLogs for the whole (source, chain)")
def t_steady_cost():
    con, s = db(), source({"ethereum": [addr(i) for i in range(1, 21)]})
    rpc, _ = run_ticks(con, s, 80)
    calls = rpc.getlogs()
    assert len(calls) == 1, f"{len(calls)} eth_getLogs calls in a run at the head (CU {rpc.cu})"
    assert isinstance(calls[0][2][0]["address"], list) and len(calls[0][2][0]["address"]) == 20


@case("events of several emitters fetched in one call are stored under their own contract")
def t_contract_column():
    con, s = db(), source({"ethereum": [addr(1), addr(2), addr(3)]})
    head0 = 26_000_000
    logs = [("ethereum", head0 - 10, 0, addr(1)), ("ethereum", head0 - 10, 1, addr(3)), ("ethereum", head0 - 9, 0, addr(3))]
    run_ticks(con, s, 30, logs=logs)
    got = dict(con.execute("SELECT contract, count(*) FROM events GROUP BY 1").fetchall())
    assert got == {addr(1): 1, addr(3): 2}, f"events per contract: {got}"
    actor = con.execute("SELECT DISTINCT actor FROM events").fetchall()
    assert actor == [("0x" + "cc" * 20,)], f"actor {actor}"


@case("an emitter added later backfills alone, then joins the others' call")
def t_laggard_merges():
    con = db()
    run_ticks(con, source({"ethereum": [addr(1), addr(2)]}), 30)
    s = source({"ethereum": [addr(1), addr(2), addr(9)]})
    rpc = FakeRpc()
    heads = {"ethereum": 26_000_000 + 75 * 30}
    li.ingest_source(con, rpc, CFG, s, heads, 100_000, {"unverified": [], "errors": []})
    calls = rpc.getlogs()
    alone = [c for c in calls if c[2][0]["address"] == addr(9)]
    together = [c for c in calls if isinstance(c[2][0]["address"], list) and len(c[2][0]["address"]) == 3]
    assert alone and len(together) == 1, f"{len(alone)} calls alone, {len(together)} with all three"
    assert len(set(cursors(con).values())) == 1, f"cursors differ: {cursors(con)}"
    assert not any(isinstance(c[2][0]["address"], str) and c[2][0]["address"] != addr(9) for c in calls), \
        "the emitters already at the head were queried one by one"


@case("tx_from source: running out of budget inside a range loses no event")
def t_tx_from_budget():
    con, s = db(), source({"ethereum": [addr(1)]}, actor="tx_from")
    head0 = 26_000_000
    logs = [("ethereum", head0 - 500 + 3 * i, 0, addr(1)) for i in range(60)]      # 60 events, all in one range
    con.execute("INSERT INTO cursors VALUES (?,?,?,?,1)", ("src.test", "ethereum", addr(1), head0 - 900))
    run_ticks(con, s, 12, share=300, logs=logs, head0=head0)
    n = con.execute("SELECT count(*) FROM events").fetchone()[0]
    assert n == 60, f"{n} of 60 events stored (the cursor moved past the others)"
    missing = con.execute("SELECT count(*) FROM events WHERE tx_from IS NULL").fetchone()[0]
    assert missing == 0, f"{missing} events without tx_from"


@case("a failing eth_getLogs for one emitter does not stop the others on that chain")
def t_one_failure():
    con, s = db(), source({"ethereum": [addr(1), addr(2), addr(3)]})
    for a, back in ((addr(1), 50_000), (addr(2), 100), (addr(3), 100)):
        con.execute("INSERT INTO cursors VALUES (?,?,?,?,1)", ("src.test", "ethereum", a, 26_000_000 - back))
    stats = {"unverified": [], "errors": []}
    rpc = FakeRpc(fail_for=[addr(1)])
    li.ingest_source(con, rpc, CFG, s, {"ethereum": 26_000_000}, 6000, stats)
    cur = cursors(con)
    assert cur[addr(2)] == cur[addr(3)] == 26_000_000 - 2 + 1, f"others not at the head: {cur}"
    assert cur[addr(1)] == 26_000_000 - 50_000 and len(stats["errors"]) == 1, f"{cur[addr(1)]}, errors {stats['errors']}"


@case("an address without code gets an unverified cursor and is never queried")
def t_unverified():
    con, s = db(), source({"ethereum": [addr(1), addr(2)]})
    stats = {"unverified": [], "errors": []}
    rpc = FakeRpc(no_code=[addr(2)])
    li.ingest_source(con, rpc, CFG, s, {"ethereum": 26_000_000}, 100_000, stats)
    assert stats["unverified"] == [f"src.test@ethereum:{addr(2)}"], stats["unverified"]
    v = dict(con.execute("SELECT contract, verified FROM cursors").fetchall())
    assert v == {addr(1): 1, addr(2): 0}, v
    for c in rpc.getlogs():
        a = c[2][0]["address"]
        assert addr(2) not in (a if isinstance(a, list) else [a]), "the unverified address was queried"


@case("a 'block range too large' answer shrinks the step and the run goes on")
def t_range_shrinks():
    con, s = db(), source({"ethereum": [addr(1), addr(2)]})
    rpc = FakeRpc(max_range=250)
    li.ingest_source(con, rpc, CFG, s, {"ethereum": 26_000_000}, 100_000, {"unverified": [], "errors": []})
    cur = cursors(con)
    assert set(cur.values()) == {26_000_000 - 2 + 1}, f"not at the head: {cur}"


@case("the budget is respected: a run overshoots by at most one call")
def t_budget():
    con, s = db(), source({"ethereum": [addr(i) for i in range(1, 21)]})
    for t in range(20):
        rpc = FakeRpc()
        li.ingest_source(con, rpc, CFG, s, {"ethereum": 26_000_000 + 75 * t}, 600, {"unverified": [], "errors": []})
        assert rpc.cu <= 660, f"run {t} used {rpc.cu} CU on a 600 CU share"


for fn in (t_all_emitters, t_second_chain, t_steady_cost, t_contract_column, t_laggard_merges, t_tx_from_budget,
           t_one_failure, t_unverified, t_range_shrinks, t_budget):
    fn()
bad = [r for r in RESULTS if not r[1]]
for name, ok, why in RESULTS:
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"\n      {why}" if why else ""))
print(f"{len(RESULTS) - len(bad)}/{len(RESULTS)} passed" + (" - ALL PASS" if not bad else ""))
sys.exit(0 if (OLD or not bad) else 1)
