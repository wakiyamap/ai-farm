#!/usr/bin/env python3
"""Phase 12e offline tests: no network, no key, nothing outside a temp directory.

  test-12e.py <farm-explorer> <explorer> <patched run-role> <patched farm.nft>

The Etherscan side is a fake inside the test (urllib.request.urlopen is replaced).
"""
import contextlib
import importlib.machinery
import importlib.util
import io
import json
import os
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

sys.dont_write_bytecode = True
if len(sys.argv) != 5:
    sys.exit(__doc__)
SVC_PATH, CLI_PATH, RUN_ROLE, NFT = sys.argv[1:]
KEY = "SECRETKEY1234567890ABCDEFGHIJKLMNOP"
ADDR = "0x" + "ab" * 20
RESULTS = []
REAL_URLOPEN = urllib.request.urlopen


def load(path, tag):
    name = f"{tag}_{time.time_ns()}"
    loader = importlib.machinery.SourceFileLoader(name, path)
    mod = importlib.util.module_from_spec(importlib.util.spec_from_loader(name, loader))
    loader.exec_module(mod)
    return mod


def case(name):
    def deco(fn):
        def run():
            try:
                with tempfile.TemporaryDirectory() as tmp:
                    fn(tmp)
                RESULTS.append((name, True, ""))
            except SystemExit as exc:
                RESULTS.append((name, False, f"exited: {exc}"))
            except Exception as exc:                       # noqa: BLE001
                RESULTS.append((name, False, f"{type(exc).__name__}: {exc}"))
            finally:
                urllib.request.urlopen = REAL_URLOPEN
        run.__name__ = "run"
        return run
    return deco


class Resp:
    def __init__(self, obj):
        self.body = json.dumps(obj).encode()

    def read(self, n=-1):
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class Upstream:
    """Stands in for Etherscan: records every query, answers from `answer(query)`."""

    def __init__(self, answer=None):
        self.queries = []
        self.answer = answer or (lambda q: {"status": "1", "message": "OK", "result": [{"ok": True}]})

    def __call__(self, req, timeout=None):
        url = req.full_url if hasattr(req, "full_url") else req
        q = {k: v[0] for k, v in urllib.parse.parse_qs(urllib.parse.urlparse(url).query).items()}
        self.queries.append(q)
        out = self.answer(q)
        if isinstance(out, Exception):
            raise out
        return Resp(out)


def service(answer=None, **cfg_extra):
    svc = load(SVC_PATH, "svc")
    svc.log = lambda **kw: None
    cfg = dict({"upstream": "https://etherscan.invalid/v2/api", "min_interval_s": 0, "daily_limit": 100,
                "chains": {"ethereum": 1, "base": 8453, "elysium": 99901}}, **cfg_extra)
    up = Upstream(answer)
    urllib.request.urlopen = up
    return svc, svc.Explorer(cfg, KEY), up


def refused(svc, fn):
    try:
        fn()
    except svc.Refused as exc:
        return exc.args[0]
    raise AssertionError("not refused")


@case("service: source / abi / creation / txs / internal / tokentx map to the fixed module and action, with the "
      "chain id and the key added")
def t_ops(tmp):
    svc, ex, up = service()
    want = {"source": ("contract", "getsourcecode"), "abi": ("contract", "getabi"),
            "creation": ("contract", "getcontractcreation"), "txs": ("account", "txlist"),
            "internal": ("account", "txlistinternal"), "tokentx": ("account", "tokentx")}
    for op, (module, action) in want.items():
        out = ex.query("ethereum", op, {"address": ADDR})
        q = up.queries[-1]
        assert (q["module"], q["action"], q["chainid"], q["apikey"]) == (module, action, "1", KEY), q
        assert out["result"] == [{"ok": True}] and out["op"] == op
    assert up.queries[2]["contractaddresses"] == ADDR and "address" not in up.queries[2]


@case("service: an unknown operation, an unknown chain, a malformed address and out-of-range numbers are refused "
      "without any upstream call")
def t_refuse(tmp):
    svc, ex, up = service()
    assert refused(svc, lambda: ex.query("ethereum", "verifysourcecode", {"address": ADDR}))[0] == 404
    assert refused(svc, lambda: ex.query("solana", "source", {"address": ADDR}))[0] == 404
    for bad in ("", "0x1234", ADDR + "00", "0x" + "zz" * 20, ADDR + "&action=x"):
        assert refused(svc, lambda: ex.query("ethereum", "source", {"address": bad}))[0] == 400, bad
    assert refused(svc, lambda: ex.query("ethereum", "txs", {"address": ADDR, "offset": "5000"}))[0] == 400
    assert refused(svc, lambda: ex.query("ethereum", "txs", {"address": ADDR, "page": "x"}))[0] == 400
    assert refused(svc, lambda: ex.query("ethereum", "tokentx", {"address": ADDR, "contractaddress": "junk"}))[0] == 400
    assert up.queries == [], up.queries


@case("service: extra query parameters from the caller (module, action, apikey, anything else) never reach upstream")
def t_no_passthrough(tmp):
    svc, ex, up = service()
    ex.query("ethereum", "txs", {"address": ADDR, "module": "proxy", "action": "eth_sendRawTransaction",
                                 "apikey": "other", "hex": "0x00", "sort": "asc", "offset": "10"})
    q = up.queries[-1]
    assert (q["module"], q["action"], q["apikey"]) == ("account", "txlist", KEY), q
    assert "hex" not in q and q["sort"] == "asc" and q["offset"] == "10" and q["page"] == "1", q


@case("service: the key is scrubbed from every error, even when the upstream or an exception echoes it")
def t_scrub(tmp):
    svc, ex, up = service(lambda q: {"status": "0", "message": "NOTOK", "result": f"bad request apikey={q['apikey']}"})
    code, why = refused(svc, lambda: ex.query("ethereum", "source", {"address": ADDR}))
    assert KEY not in why and "***" in why, why
    svc, ex, up = service(lambda q: urllib.error.URLError(f"cannot reach https://x/?apikey=<REDACTED>'apikey']}"))
    code, why = refused(svc, lambda: ex.query("ethereum", "source", {"address": ADDR}))
    assert code == 502 and KEY not in why, why


@case("service: 'Free API access is not supported for this chain' -> 402 with a hint, chain marked not_on_plan; "
      "an invalid key -> 503; an unverified contract -> 422 with Etherscan's words")
def t_classify(tmp):
    msg = "Free API access is not supported for this chain. Please upgrade your api plan for full chain coverage."
    svc, ex, up = service(lambda q: {"status": "0", "message": "NOTOK", "result": msg})
    code, why = refused(svc, lambda: ex.query("base", "source", {"address": ADDR}))
    assert code == 402 and "Routescan" in why and ex.status["base"] == "not_on_plan", (code, why)
    svc, ex, up = service(lambda q: {"status": "0", "message": "NOTOK", "result": "Missing/Invalid API Key"})
    assert refused(svc, lambda: ex.query("ethereum", "abi", {"address": ADDR}))[0] == 503
    assert ex.status["ethereum"] == "invalid_key"
    svc, ex, up = service(lambda q: {"status": "0", "message": "NOTOK", "result": "Contract source code not verified"})
    code, why = refused(svc, lambda: ex.query("ethereum", "abi", {"address": ADDR}))
    assert code == 422 and "not verified" in why, why


@case("service: 'No transactions found' (status 0, empty list) is an answer, not an error")
def t_empty(tmp):
    svc, ex, up = service(lambda q: {"status": "0", "message": "No transactions found", "result": []})
    assert ex.query("ethereum", "txs", {"address": ADDR})["result"] == []
    assert ex.status["ethereum"] == "ok"


@case("service: source / abi / creation answers are cached (second call makes no upstream call); tx lists are not; "
      "errors are not cached")
def t_cache(tmp):
    svc, ex, up = service()
    ex.query("ethereum", "source", {"address": ADDR})
    ex.query("ethereum", "source", {"address": ADDR.upper().replace("0X", "0x")})
    assert len(up.queries) == 1 and ex.stats["cache_hits"] == 1, (len(up.queries), ex.stats)
    ex.query("ethereum", "txs", {"address": ADDR})
    ex.query("ethereum", "txs", {"address": ADDR})
    assert len(up.queries) == 3
    svc, ex, up = service(lambda q: {"status": "0", "message": "NOTOK", "result": "Max rate limit reached"})
    for _ in range(2):
        assert refused(svc, lambda: ex.query("ethereum", "abi", {"address": ADDR}))[0] == 429
    assert len(up.queries) == 2


@case("service: the daily limit stops upstream calls with 429 and resets on the next UTC day")
def t_daily(tmp):
    svc, ex, up = service(daily_limit=3)
    for _ in range(3):
        ex.query("ethereum", "txs", {"address": ADDR})
    assert refused(svc, lambda: ex.query("ethereum", "txs", {"address": ADDR}))[0] == 429
    assert len(up.queries) == 3
    ex.day = "2000-01-01"
    ex.query("ethereum", "txs", {"address": ADDR})
    assert len(up.queries) == 4 and ex.calls_today == 1


@case("service: calls are spaced by min_interval_s")
def t_interval(tmp):
    svc, ex, up = service(min_interval_s=0.4)
    slept = []
    svc.time.sleep = slept.append
    ex.query("ethereum", "txs", {"address": ADDR})
    ex.query("ethereum", "txs", {"address": ADDR})
    assert len(slept) == 1 and 0 < slept[0] <= 0.4, slept


@case("service: the chain table probes each chain once (ok / not_on_plan / unsupported) and remembers it")
def t_chains(tmp):
    def answer(q):
        if q["chainid"] == "1":
            return {"jsonrpc": "2.0", "id": 83, "result": "0x16b3a1c"}
        if q["chainid"] == "8453":
            return {"status": "0", "message": "NOTOK", "result": "Free API access is not supported for this chain."}
        return {"status": "0", "message": "NOTOK", "result": "Missing or unsupported chainid parameter (required for v2 api)"}
    svc, ex, up = service(answer)
    table = ex.chain_table()
    assert {c: v["status"] for c, v in table.items()} == {"ethereum": "ok", "base": "not_on_plan", "elysium": "unsupported"}, table
    assert all(q["action"] == "eth_blockNumber" for q in up.queries) and len(up.queries) == 3
    ex.chain_table()
    assert len(up.queries) == 3, "probed again without probe=1"
    ex.chain_table(probe=True)
    assert len(up.queries) == 6


@case("service over HTTP: GET answers, POST is refused, an unknown path is 404, the key is in no response")
def t_http(tmp):
    svc, ex, up = service()
    srv = svc.ThreadingHTTPServer(("127.0.0.1", 0), svc.make_handler(ex))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_address[1]}"
    try:
        def fetch(path, data=None):
            try:
                with REAL_URLOPEN(urllib.request.Request(base + path, data=data), timeout=10) as r:
                    return r.status, r.read().decode()
            except urllib.error.HTTPError as exc:
                return exc.code, exc.read().decode()
        code, body = fetch(f"/q/ethereum/abi?address={ADDR}")
        assert code == 200 and json.loads(body)["op"] == "abi", (code, body)
        assert fetch("/health")[0] == 200 and KEY not in fetch("/health")[1]
        assert fetch(f"/q/ethereum/abi?address={ADDR}", data=b"{}")[0] == 405
        assert fetch("/etc/passwd")[0] == 404
        code, body = fetch("/q/ethereum/source?address=nope")
        assert code == 400 and "error" in json.loads(body) and KEY not in body
    finally:
        srv.shutdown()


# --- CLI ----------------------------------------------------------------------------------------

@case("cli: SourceCode in all three Etherscan shapes (plain, {{standard-json}}, {files}) becomes a file map")
def t_cli_shapes(tmp):
    cli = load(CLI_PATH, "cli")
    one = cli.source_files({"SourceCode": "contract A {}", "ContractName": "A", "CompilerVersion": "v0.8.24"})
    assert one == {"A.sol": "contract A {}"}, one
    std = json.dumps({"language": "Solidity", "sources": {"src/A.sol": {"content": "a"}, "lib/B.sol": {"content": "b"}}})
    assert cli.source_files({"SourceCode": "{" + std + "}", "ContractName": "A"}) == {"src/A.sol": "a", "lib/B.sol": "b"}
    multi = json.dumps({"A.sol": {"content": "a"}, "B.sol": {"content": "b"}})
    assert cli.source_files({"SourceCode": multi, "ContractName": "A"}) == {"A.sol": "a", "B.sol": "b"}
    vy = cli.source_files({"SourceCode": "# @version 0.3.10", "ContractName": "V", "CompilerVersion": "vyper:0.3.10"})
    assert list(vy) == ["V.vy"], vy


@case("cli: --out never writes outside the directory, whatever the explorer names the files")
def t_cli_paths(tmp):
    cli = load(CLI_PATH, "cli")
    root = os.path.join(tmp, "out")
    for rel in ("../../etc/passwd", "/etc/passwd", "a/../../b.sol", "..\\..\\x.sol", "", "./ok/A.sol"):
        dest = os.path.abspath(cli.safe_path(root, rel))
        assert dest.startswith(os.path.abspath(root) + os.sep), (rel, dest)


@case("cli: `explorer source --out` prints the summary (proxy and implementation included) and writes the files; "
      "`explorer abi` prints signatures")
def t_cli_run(tmp):
    cli = load(CLI_PATH, "cli")
    std = json.dumps({"sources": {"src/Hook.sol": {"content": "contract Hook {}"}}})
    entry = {"SourceCode": "{" + std + "}", "ContractName": "Hook", "CompilerVersion": "v0.8.26", "OptimizationUsed": "1",
             "Runs": "200", "EVMVersion": "cancun", "LicenseType": "MIT", "Proxy": "1", "Implementation": "0x" + "cd" * 20,
             "ABI": "[]", "ConstructorArguments": ""}
    abi = [{"type": "function", "name": "exitAll", "inputs": [], "outputs": [], "stateMutability": "nonpayable"},
           {"type": "function", "name": "quote", "stateMutability": "view", "outputs": [{"type": "uint256"}],
            "inputs": [{"type": "tuple", "components": [{"type": "address"}, {"type": "uint24"}]}, {"type": "uint256"}]},
           {"type": "event", "name": "Swap", "inputs": [{"type": "address", "indexed": True}, {"type": "int256"}]}]

    def get(path, **params):
        return {"result": [entry]} if path.endswith("/source") else {"result": json.dumps(abi)}
    cli.get = get
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        assert cli.main(["source", "ethereum", ADDR, "--out", os.path.join(tmp, "o")]) == 0
        assert cli.main(["abi", "ethereum", ADDR]) == 0
    text = out.getvalue()
    assert "name: Hook" in text and "implementation 0x" + "cd" * 20 in text and "src/Hook.sol" in text, text
    assert open(os.path.join(tmp, "o", "src", "Hook.sol")).read() == "contract Hook {}"
    assert "exitAll()" in text and "quote((address,uint24),uint256) view -> (uint256)" in text, text
    assert "event Swap(address,int256)" in text


@case("cli: an unverified contract and a service that is down end with a one-line message and a non-zero exit")
def t_cli_errors(tmp):
    cli = load(CLI_PATH, "cli")
    cli.get = lambda path, **p: {"result": [{"SourceCode": "", "ABI": "Contract source code not verified"}]}
    try:
        cli.main(["source", "ethereum", ADDR])
        raise AssertionError("no exit")
    except SystemExit as exc:
        assert "no verified source" in str(exc)
    cli2 = load(CLI_PATH, "cli")
    cli2.BASE = "http://127.0.0.1:9"
    try:
        cli2.main(["chains"])
        raise AssertionError("no exit")
    except SystemExit as exc:
        assert "failed" in str(exc)


# --- patched files ------------------------------------------------------------------------------

@case("run-role: every claude role may run `explorer`; WebFetch is in the researcher's list and in no other role's")
def t_run_role(tmp):
    text = open(RUN_ROLE, encoding="utf-8").read()
    common = next(ln for ln in text.splitlines() if ln.strip().startswith("local common="))
    assert "Bash(explorer *)" in common and "WebFetch" not in common, common
    lines = text.splitlines()
    roles = {}
    cur = None
    for ln in lines:
        s = ln.strip()
        if s.endswith(")") and s[:-1] in ("meta", "live-operator", "paper-reviewer", "researcher", "*"):
            cur = s[:-1]
        elif cur and s.startswith("echo "):
            roles[cur] = s
            cur = None
    assert set(roles) == {"meta", "live-operator", "paper-reviewer", "researcher", "*"}, roles.keys()
    assert ",WebFetch," in roles["researcher"], roles["researcher"]
    assert all("WebFetch" not in v for k, v in roles.items() if k != "researcher")
    assert "Bash(gate promote *)" in roles["paper-reviewer"] and "Bash(gate *)" in roles["live-operator"]


@case("farm.nft: 29484 is open to the earner and not to the bots")
def t_nft(tmp):
    text = open(NFT, encoding="utf-8").read()
    earner = next(ln for ln in text.splitlines() if "skuid earner" in ln and "tcp dport" in ln)
    bot = next(ln for ln in text.splitlines() if "skuid farmbot" in ln and "tcp dport" in ln)
    assert "29483, 29484 }" in earner, earner
    assert "29484" not in bot and "29483" not in bot, bot


for fn in list(globals().values()):
    if callable(fn) and getattr(fn, "__name__", "") == "run":
        fn()

print("== phase 12e")
for name, ok, why in RESULTS:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"\n        {why}" if why else ""))
failed = [r for r in RESULTS if not r[1]]
print(f"{len(RESULTS) - len(failed)} of {len(RESULTS)} passed")
print("ALL PASS" if not failed else f"{len(failed)} FAILED")
sys.exit(1 if failed else 0)
