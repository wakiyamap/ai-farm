#!/usr/bin/env python3
"""Phase 10j offline tests: fork reset on elysium, and relay-wait (local sockets only, no chain).

  test-10j.py <fork> <relay-wait> [--old]

With --old the failures are only reported (they show what the installed fork does today).
"""
import contextlib
import importlib.machinery
import importlib.util
import io
import json
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

args = [a for a in sys.argv[1:] if a != "--old"]
OLD = "--old" in sys.argv
sys.dont_write_bytecode = True
if len(args) != 2:
    sys.exit(__doc__)
FORK, WAIT = args
RESULTS = []


def load(path, tag):
    name = f"{tag}_{time.time_ns()}"
    loader = importlib.machinery.SourceFileLoader(name, path)
    mod = importlib.util.module_from_spec(importlib.util.spec_from_loader(name, loader))
    loader.exec_module(mod)
    return mod


def case(name):
    def deco(fn):
        def run():
            err = io.StringIO()
            try:
                with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
                    fn(err)
                RESULTS.append((name, True, ""))
            except SystemExit as exc:
                RESULTS.append((name, False, f"exited: {err.getvalue().strip()[-200:] or exc}"))
            except Exception as exc:                       # noqa: BLE001
                RESULTS.append((name, False, f"{type(exc).__name__}: {exc}"))
        run.__name__ = "run"
        return run
    return deco


def fork_with_fakes(mine_error=None):
    f = load(FORK, "fork")
    calls = []

    def rpc(u, method, params):
        calls.append(method)
        return "0x10" if method == "eth_blockNumber" else None

    def rpc_raw(u, method, params):
        calls.append(method)
        return {"error": {"message": mine_error}} if mine_error else {"result": "0x0"}
    f.rpc, f.rpc_raw = rpc, rpc_raw
    f.guard_lease = lambda chain, force=False: None
    f.bump_generation = lambda chain: 7
    return f, calls


@case("fork reset elysium mines one block after the reset and says so")
def t_elysium(err):
    f, calls = fork_with_fakes()
    f.cmd_reset("elysium")
    assert calls[:2] == ["anvil_reset", "evm_mine"], f"calls: {calls}"
    assert "one block past" in err.getvalue(), err.getvalue()


@case("fork reset on the other chains is unchanged (no extra block)")
def t_others(err):
    for chain in ("base", "arbitrum", "ethereum", "hyperevm", "ethereum-review"):
        f, calls = fork_with_fakes()
        f.cmd_reset(chain)
        assert "evm_mine" not in calls, f"{chain}: {calls}"


@case("a failing evm_mine does not fail the reset (warning only, generation still bumped)")
def t_mine_fails(err):
    f, calls = fork_with_fakes(mine_error="boom")
    bumped = []
    f.bump_generation = lambda chain: bumped.append(chain) or 8
    f.cmd_reset("elysium", "123")
    assert bumped == ["elysium"] and "warning" in err.getvalue(), f"bumped {bumped}; {err.getvalue()}"


class Relay(BaseHTTPRequestHandler):
    fail_first = 0
    seen = 0

    def log_message(self, *a):
        pass

    def do_POST(self):
        type(self).seen += 1
        self.rfile.read(int(self.headers.get("Content-Length", 0)))
        if type(self).seen <= type(self).fail_first:
            body = json.dumps({"jsonrpc": "2.0", "id": 1, "error": {"code": -32000, "message": "all providers failed: no provider available"}})
        else:
            body = json.dumps({"jsonrpc": "2.0", "id": 1, "result": "0x1920000"})
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body.encode())


def serve(fail_first):
    Relay.fail_first, Relay.seen = fail_first, 0
    srv = HTTPServer(("127.0.0.1", 0), Relay)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


@case("relay-wait returns as soon as the relay answers (two errors first)")
def t_wait_ok(err):
    w = load(WAIT, "wait")
    srv = serve(2)
    try:
        t0 = time.monotonic()
        rc = w.main(["20"], url=f"http://127.0.0.1:{srv.server_port}", pause=0.05)
        assert rc == 0 and Relay.seen == 3 and time.monotonic() - t0 < 5, f"rc {rc}, requests {Relay.seen}"
        assert "relay answers" in err.getvalue(), err.getvalue()
    finally:
        srv.shutdown()


@case("relay-wait gives up after the limit and still exits 0 (the signer must get its start)")
def t_wait_timeout(err):
    w = load(WAIT, "wait")
    srv = serve(10**6)
    try:
        t0 = time.monotonic()
        rc = w.main(["0.5"], url=f"http://127.0.0.1:{srv.server_port}", pause=0.1)
        took = time.monotonic() - t0
        assert rc == 0 and took < 3, f"rc {rc}, took {took:.1f}s"
        assert "starting anyway" in err.getvalue(), err.getvalue()
    finally:
        srv.shutdown()


@case("relay-wait treats a closed port as 'not yet' (no traceback)")
def t_wait_refused(err):
    w = load(WAIT, "wait")
    rc = w.main(["0.3"], url="http://127.0.0.1:9", pause=0.1)
    assert rc == 0 and "Traceback" not in err.getvalue(), err.getvalue()


for fn in list(globals().values()):
    if callable(fn) and getattr(fn, "__name__", "") == "run":
        fn()

print(f"== {'before 10j (installed fork)' if OLD else 'phase 10j'}")
for name, ok, why in RESULTS:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"\n        {why}" if why else ""))
failed = [r for r in RESULTS if not r[1]]
if not OLD:
    print("ALL PASS" if not failed else f"{len(failed)} FAILED")
    sys.exit(1 if failed else 0)
