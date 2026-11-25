#!/usr/bin/env python3
"""Offline tests for phase 10a (no network, no root; a fake relay on a random local port).

  test-10a.py <fork> <farm.nft> <common.md> <ledger-ingest> <cfg-10a.py> [--old]

--old runs the same checks against the installed (unpatched) files: failures there are expected
and informational. Without --old every case must pass.
"""
import contextlib
import http.server
import importlib.machinery
import importlib.util
import io
import json
import os
import sqlite3
import sys
import tempfile
import threading
import traceback

args = [a for a in sys.argv[1:] if a != "--old"]
OLD = "--old" in sys.argv
if len(args) != 5:
    sys.exit(__doc__)
FORK, NFT, COMMON, LEDGER, CFG = args
NEW = ["bsc", "polygon", "avalanche", "optimism", "hyperevm"]
RESULTS = []


def load(path, name):
    loader = importlib.machinery.SourceFileLoader(name, path)
    spec = importlib.util.spec_from_loader(name, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def case(title):
    def wrap(fn):
        def run():
            with tempfile.TemporaryDirectory() as tmp:
                try:
                    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                        fn(tmp)
                    RESULTS.append((title, True, ""))
                except SystemExit as exc:
                    RESULTS.append((title, False, f"SystemExit {exc}"))
                except Exception as exc:                       # noqa: BLE001 - report every failure
                    RESULTS.append((title, False, f"{type(exc).__name__}: {exc}\n"
                                    + "".join(traceback.format_tb(exc.__traceback__)[-2:])))
        run.__name__ = "run"
        return run
    return wrap


# ---------------------------------------------------------------- fake relay
class Fake:
    ids = {"base": 8453, "arbitrum": 42161, "ethereum": 1, "bsc": 56, "polygon": 137, "avalanche": 43114,
           "optimism": 10, "hyperevm": 999}
    block_time = {"bsc": 0.45, "polygon": 2.0, "avalanche": 1.7, "optimism": 2.0, "hyperevm": 1.0, "base": 2.0}
    down = set()
    calls = []
    wrong_desc = set()
    head = 50_000_000


def abi_str(s):
    b = s.encode()
    return "0x" + (32).to_bytes(32, "big").hex() + len(b).to_bytes(32, "big").hex() + b.ljust(32, b"\0").hex()


class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):
        chain = self.path.split("?")[0].strip("/")
        req = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        Fake.calls.append((chain, req["method"]))
        if chain in Fake.down:
            self.send_response(500)
            self.end_headers()
            return
        m, p = req["method"], req.get("params", [])
        res = None
        if m == "eth_chainId":
            res = hex(Fake.ids[chain])
        elif m == "eth_blockNumber":
            res = hex(Fake.head)
        elif m == "eth_getBlockByNumber":
            res = {"timestamp": hex(int(int(p[0], 16) * Fake.block_time.get(chain, 2.0)))}
        elif m == "eth_getCode":
            res = "0x6080"
        elif m == "eth_getLogs":
            res = []
        elif m == "eth_call":
            cfg = CFGMOD.NEW[chain]
            to, sel = p[0]["to"], p[0]["data"]
            feed = to.lower() == cfg["feed"].lower()
            if sel == "0x313ce567":
                res = hex(8 if feed else cfg["usdc_decimals"])
            elif sel == "0x7284e416":
                res = abi_str("XXX / USD" if chain in Fake.wrong_desc else cfg["desc"][0])
            elif sel == "0x50d25bcd":
                res = hex(123_45000000)
            elif sel == "0x95d89b41":
                res = abi_str("USDC")
        body = json.dumps({"jsonrpc": "2.0", "id": req.get("id"), "result": res}).encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
threading.Thread(target=srv.serve_forever, daemon=True).start()
RELAY = f"http://127.0.0.1:{srv.server_address[1]}"
CFGMOD = load(CFG, "cfg10a")
CFGMOD.RELAY = RELAY


def reset_fake():
    Fake.down, Fake.calls, Fake.wrong_desc = set(), [], set()


def sample_etc(tmp):
    etc = os.path.join(tmp, "etc")
    os.makedirs(etc)
    with open(f"{etc}/chains", "w") as f:
        f.write("# Chains the farm works on. Used by the KB writer (and later the RPC relay).\nbase\narbitrum\nethereum\n")
    relay = {"bind": "127.0.0.1", "port": 8545,
             "chains": {"base": {"alchemy": "base-mainnet", "public": ["https://example.invalid/base"]},
                        "arbitrum": {"alchemy": "arb-mainnet", "public": ["https://example.invalid/arb"]},
                        "ethereum": {"alchemy": "eth-mainnet", "public": ["https://example.invalid/eth"]}},
             "alchemy_daily_cu": {"live": 1500000, "paper": 900000, "research": 1000000}}
    with open(f"{etc}/relay.json", "w") as f:
        json.dump(relay, f, indent=2)
    led = {"relay_url": RELAY, "lane": "research", "db": f"{tmp}/ledger/ledger.db",
           "seed_sources": f"{etc}/ledger-sources.json", "agent_sources_dir": f"{tmp}/sources.d",
           "backfill_days": 7, "blocks_per_call": {"ethereum": 2000, "base": 5000, "arbitrum": 10000},
           "block_time_s": {"ethereum": 12, "base": 2, "arbitrum": 0.25}, "max_cu_per_run": 20000,
           "max_cu_per_run_agent_sources": 6000, "max_agent_sources": 40, "confirmations": 12}
    with open(f"{etc}/ledger.json", "w") as f:
        json.dump(led, f, indent=2)
    for p in ("chains", "relay.json", "ledger.json"):
        os.chmod(f"{etc}/{p}", 0o640)
    return etc


# ---------------------------------------------------------------- patched files
@case("fork: ports 9004-9008 for the five new chains, help lists them")
def t_fork(tmp):
    fk = load(FORK, "fork10a")
    want = {"bsc": 9004, "polygon": 9005, "avalanche": 9006, "optimism": 9007, "hyperevm": 9008}
    for c, p in want.items():
        assert fk.PORTS.get(c) == p, (c, fk.PORTS.get(c))
        assert fk.url(c) == f"http://127.0.0.1:{p}"
    assert fk.PORTS["ethereum-review"] == 9013 and fk.PORTS["base"] == 9001
    assert all(c in fk.__doc__ for c in want), "help text lacks a chain"


@case("farm.nft: earner and bots reach 9001-9008, 9013 still closed")
def t_nft(tmp):
    t = open(NFT).read()
    assert t.count("9001-9008") == 3 and "9001-9003" not in t, t.count("9001-9008")
    rules = [l for l in t.splitlines() if "dport !=" in l and "tcp" in l]
    assert len(rules) == 2 and all("9013" not in r for r in rules), rules


@case("common.md: eight chains with ids and farm names, gate caveat, BSC USDC decimals")
def t_common(tmp):
    t = open(COMMON).read()
    for s in ("Base (chain id 8453)", "BNB Smart Chain (56)", "Polygon PoS (137)", "Avalanche C-Chain (43114)",
              "OP Mainnet (10)", "HyperEVM (999)", "`hyperevm`", "18 decimals", "gate cannot fund or promote"):
        assert s in t, s


def ledger_cfg(tmp, sources):
    etc = sample_etc(tmp)
    led = json.load(open(f"{etc}/ledger.json"))
    led["blocks_per_call"].update({"bsc": 10000, "polygon": 3600})
    led["block_time_s"].update({"bsc": 0.45, "polygon": 2.0})
    with open(f"{etc}/ledger.json", "w") as f:
        json.dump(led, f)
    with open(led["seed_sources"], "w") as f:
        json.dump({"sources": sources}, f)
    os.makedirs(led["agent_sources_dir"])
    return f"{etc}/ledger.json", led


@case("ledger-ingest: a chain whose head is unreadable is skipped, the run completes")
def t_ledger(tmp):
    reset_fake()
    li = load(LEDGER, "li10a")
    ev = "Transfer(address,address,uint256)"
    src = {"id": "t-transfer", "protocol": "test", "kind": "transfer", "event": ev, "topic0": li.keccak(ev),
           "indexed": ["from", "to"], "data": ["value"], "actor_field": "from",
           "chains": {"base": ["0x" + "11" * 20], "bsc": ["0x" + "22" * 20]}}
    li.CONFIG_PATH, led = ledger_cfg(tmp, [src])
    Fake.down = {"bsc", "polygon"}
    li.main()
    con = sqlite3.connect(led["db"])
    note = con.execute("SELECT note FROM runs ORDER BY id DESC LIMIT 1").fetchone()[0] or ""
    cur = dict(((c, n) for c, n in con.execute("SELECT chain, next_block FROM cursors")))
    assert "bsc" in note, note
    assert cur.get("base", 0) > 0 and "bsc" not in cur, cur
    assert ("polygon", "eth_blockNumber") not in Fake.calls, "head read for a chain no source uses"


# ---------------------------------------------------------------- cfg-10a
@case("cfg apply: chains / relay.json / fork-<chain>.env added, existing kept, mode kept, idempotent")
def t_apply(tmp):
    etc = sample_etc(tmp)
    before = json.load(open(f"{etc}/relay.json"))
    CFGMOD.apply(etc)
    CFGMOD.apply(etc)
    lines = open(f"{etc}/chains").read().splitlines()
    assert lines[0].startswith("#") and lines[1:] == ["base", "arbitrum", "ethereum"] + NEW, lines
    after = json.load(open(f"{etc}/relay.json"))
    for k in before["chains"]:
        assert after["chains"][k] == before["chains"][k]
    assert after["alchemy_daily_cu"] == before["alchemy_daily_cu"]
    assert after["chains"]["hyperevm"] == {"alchemy": "hyperliquid-mainnet",
                                           "public": ["https://rpc.hyperliquid.xyz/evm"]}
    assert oct(os.stat(f"{etc}/relay.json").st_mode & 0o777) == "0o640"
    env = open(f"{etc}/fork-avalanche.env").read()
    assert env == "FORK_PORT=9006\nFORK_CHAIN_ID=43114\nFORK_UPSTREAM=avalanche\n", env


@case("cfg ledger: block time measured through the relay, blocks_per_call ~2 h, existing chains unchanged")
def t_cfg_ledger(tmp):
    reset_fake()
    etc = sample_etc(tmp)
    CFGMOD.ledger(etc)
    led = json.load(open(f"{etc}/ledger.json"))
    assert led["blocks_per_call"]["base"] == 5000 and led["block_time_s"]["arbitrum"] == 0.25
    assert led["block_time_s"]["bsc"] == 0.45 and led["blocks_per_call"]["bsc"] == 10000, led
    assert led["block_time_s"]["polygon"] == 2.0 and led["blocks_per_call"]["polygon"] == 3600, led
    assert led["blocks_per_call"]["avalanche"] == 4200, led
    n = len(Fake.calls)
    CFGMOD.ledger(etc)                                   # second run: nothing to measure
    assert len(Fake.calls) == n


@case("cfg verify: chain id, feed and USDC read through the relay; a wrong description is flagged")
def t_verify(tmp):
    reset_fake()
    Fake.wrong_desc = {"polygon"}
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        CFGMOD.verify()
    out = buf.getvalue()
    assert "verify ok" in out, out
    assert "\"BNB / USD\"" in out and "decimals 18" in out, out
    pol = [l for l in out.splitlines() if l.strip().startswith("polygon") and "feed" in l]
    assert pol and "CHECK" in pol[0], pol
    Fake.down = {"hyperevm"}
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            CFGMOD.verify()
        raise AssertionError("verify passed with a chain down")
    except SystemExit:
        pass


for fn in list(globals().values()):
    if callable(fn) and getattr(fn, "__name__", "") == "run":
        fn()

print(f"== {'before 10a (installed files)' if OLD else 'phase 10a'}")
for name, ok, why in RESULTS:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"\n        {why}" if why else ""))
failed = [r for r in RESULTS if not r[1]]
if not OLD:
    print("ALL PASS" if not failed else f"{len(failed)} FAILED")
    sys.exit(1 if failed else 0)
