#!/usr/bin/env python3
"""Offline tests for phase 15a: farm-explorer with an Etherscan and a Blockscout backend, and the
explorer CLI, against two local mock upstreams. No network, no real keys.

  python3 -I test-15a.py <dir with farm-explorer and explorer>
"""
import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

SRC = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else "new")
EKEY, BKEY = "ETHERSCANTESTKEY123", "proapi_BLOCKSCOUTTESTKEY456"
CHAINS = {"ethereum": 1, "base": 8453, "arbitrum": 42161, "elysium": 99901}
ADDR = "0x" + "11" * 20
calls = {"etherscan": [], "blockscout": []}

VERIFIED_ES = [{"SourceCode": "contract A {}", "ABI": "[]", "ContractName": "A", "CompilerVersion": "v0.8.20",
                "Proxy": "0", "Implementation": ""}]
VERIFIED_BS = [{"SourceCode": "contract B {}", "ABI": "[]", "ContractName": "B", "FileName": "src/B.sol",
                "CompilerVersion": "v0.8.24", "IsProxy": "true", "ImplementationAddress": "0x" + "22" * 20,
                "AdditionalSources": [{"Filename": "src/lib/L.sol", "SourceCode": "library L {}"}]}]


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def mock(name):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_GET(self):  # noqa: N802
            q = {k: v[0] for k, v in urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query).items()}
            calls[name].append(q)
            status, body = 200, None
            if name == "etherscan":
                assert q.get("apikey") == EKEY and "chainid" in q, q
                cid = q["chainid"]
                if cid == "8453":
                    body = {"status": "0", "message": "NOTOK",
                            "result": "Free API access is not supported for this chain. Please upgrade your api plan"}
                elif cid == "99901":
                    body = {"status": "0", "message": "NOTOK", "result": "Missing or unsupported chainid parameter"}
                elif q.get("module") == "proxy":
                    body = {"jsonrpc": "2.0", "id": 1, "result": "0x10"}
                elif cid == "42161" and q.get("action") == "getsourcecode":
                    body = {"status": "1", "message": "OK", "result": [{"SourceCode": "", "ABI": "Contract source code not verified"}]}
                elif cid == "42161" and q.get("action") == "getabi":
                    body = {"status": "0", "message": "NOTOK", "result": "Contract source code not verified"}
                elif q.get("action") == "getsourcecode":
                    body = {"status": "1", "message": "OK", "result": VERIFIED_ES}
                else:
                    body = {"status": "1", "message": "OK", "result": [{"hash": "0xab", "from": ADDR, "to": ADDR}]}
            else:
                assert q.get("apikey") in (BKEY, "proapi_BAD") and "chain_id" in q, q
                if q["apikey"] == "proapi_BAD":
                    status, body = 401, None
                elif q["chain_id"] == "99901":
                    status, body = 404, {"message": f"Chain not found (key {q['apikey']})"}
                elif q.get("module") == "block":
                    body = {"jsonrpc": "2.0", "id": 1, "result": "0x20"}
                elif q.get("action") == "getsourcecode":
                    body = {"status": "1", "message": "OK", "result": VERIFIED_BS}
                elif q.get("action") == "getabi":
                    body = {"status": "1", "message": "OK", "result": "[{\"type\":\"function\",\"name\":\"f\",\"inputs\":[]}]"}
                else:
                    body = {"status": "1", "message": "OK", "result": [{"hash": "0xcd", "from": ADDR, "to": ADDR}]}
            raw = json.dumps(body).encode() if body is not None else b"Unauthorized"
            self.send_response(status)
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
    port = free_port()
    srv = ThreadingHTTPServer(("127.0.0.1", port), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return port


def start_service(tmp, es_port, bs_port, bkey):
    port = free_port()
    cred = os.path.join(tmp, f"cred-{port}")
    os.makedirs(cred)
    cfg = {"listen": ["127.0.0.1", port], "upstream": f"http://127.0.0.1:{es_port}/v2/api", "chains": CHAINS,
           "min_interval_s": 0, "daily_limit": 1000, "timeout_s": 5,
           "blockscout": {"upstream": f"http://127.0.0.1:{bs_port}/v2/api", "min_interval_s": 0, "daily_limit": 1000}}
    json.dump(cfg, open(os.path.join(cred, "conf"), "w"))
    open(os.path.join(cred, "key"), "w").write(EKEY + "\n")
    if bkey:
        open(os.path.join(cred, "bkey"), "w").write(bkey + "\n")
    env = dict(os.environ, CREDENTIALS_DIRECTORY=cred)
    p = subprocess.Popen([sys.executable, "-I", "-B", os.path.join(SRC, "farm-explorer")], env=env,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    base = f"http://127.0.0.1:{port}"
    for _ in range(50):
        try:
            urllib.request.urlopen(base + "/health", timeout=1)
            return p, base
        except Exception:  # noqa: BLE001
            time.sleep(0.1)
    p.kill()
    sys.exit("service did not start: " + p.stdout.read().decode()[-2000:])


def get(base, path):
    try:
        with urllib.request.urlopen(base + path, timeout=10) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode()


failed = 0


def check(name, cond, detail=""):
    global failed
    print(("  ok   " if cond else "  FAIL ") + name + ("" if cond else f"  -- {detail[:300]}"))
    failed += not cond


def main():
    tmp = tempfile.mkdtemp(prefix="t15a-")
    es, bs = mock("etherscan"), mock("blockscout")
    p, base = start_service(tmp, es, bs, BKEY)
    seen = []
    try:
        s, b = get(base, f"/q/ethereum/source?address={ADDR}")
        seen.append(b)
        check("ethereum source via etherscan", s == 200 and json.loads(b)["via"] == "etherscan", b)

        n_es = len(calls["etherscan"])
        s, b = get(base, f"/q/base/abi?address={ADDR}")
        seen.append(b)
        check("base abi falls back to blockscout", s == 200 and json.loads(b)["via"] == "blockscout", b)
        s, b = get(base, f"/q/base/txs?address={ADDR}")
        seen.append(b)
        check("base txs via blockscout", s == 200 and json.loads(b)["via"] == "blockscout", b)
        check("etherscan asked once for base, then skipped", len(calls["etherscan"]) == n_es + 1,
              str(len(calls["etherscan"]) - n_es))

        s, b = get(base, f"/q/arbitrum/source?address={ADDR}")
        seen.append(b)
        check("arbitrum unverified on etherscan -> blockscout source",
              s == 200 and json.loads(b)["via"] == "blockscout" and json.loads(b)["result"][0]["ContractName"] == "B", b)
        s, b = get(base, f"/q/arbitrum/abi?address={ADDR}")
        seen.append(b)
        check("arbitrum abi not verified on etherscan -> blockscout", s == 200 and json.loads(b)["via"] == "blockscout", b)
        s, b = get(base, f"/q/arbitrum/txs?address={ADDR}")
        seen.append(b)
        check("arbitrum txs stays on etherscan", s == 200 and json.loads(b)["via"] == "etherscan", b)

        s, b = get(base, f"/q/elysium/source?address={ADDR}")
        seen.append(b)
        check("elysium: both refuse -> 404 with both reasons", s == 404 and "etherscan" in b and "blockscout" in b, b)

        s, b = get(base, "/chains?probe=1")
        seen.append(b)
        t = json.loads(b)["chains"]
        check("chains: base ok via blockscout, etherscan not_on_plan",
              t["base"]["status"] == "ok" and t["base"]["via"] == "blockscout" and t["base"]["etherscan"] == "not_on_plan", b)
        check("chains: ethereum ok via etherscan", t["ethereum"]["via"] == "etherscan", b)
        check("chains: elysium no backend", t["elysium"]["status"] != "ok" and t["elysium"]["via"] is None, b)

        s, b = get(base, "/health")
        seen.append(b)
        h = json.loads(b)
        check("health keeps the 12e keys and adds backends",
              all(k in h for k in ("calls_today", "daily_limit", "chains", "upstream_ok")) and "blockscout" in h["backends"], b)

        s, b = get(base, f"/q/base/source?address=0x12")
        check("bad address refused", s == 400, b)

        # CLI
        env = dict(os.environ, EXPLORER_URL=base)
        cli = [sys.executable, "-I", os.path.join(SRC, "explorer")]
        r = subprocess.run(cli + ["chains"], env=env, capture_output=True, text=True)
        seen.append(r.stdout + r.stderr)
        check("cli chains", r.returncode == 0 and "base: ok via blockscout" in r.stdout, r.stdout + r.stderr)
        out = os.path.join(tmp, "src")
        r = subprocess.run(cli + ["source", "base", ADDR, "--out", out], env=env, capture_output=True, text=True)
        seen.append(r.stdout + r.stderr)
        check("cli source via blockscout, proxy line, two files written",
              r.returncode == 0 and "via: blockscout" in r.stdout and "implementation 0x2222" in r.stdout
              and os.path.exists(os.path.join(out, "src/B.sol")) and os.path.exists(os.path.join(out, "src/lib/L.sol")),
              r.stdout + r.stderr)
        r = subprocess.run(cli + ["abi", "base", ADDR], env=env, capture_output=True, text=True)
        check("cli abi", r.returncode == 0 and "f()" in r.stdout, r.stdout + r.stderr)
        r = subprocess.run(cli + ["source", "ethereum", ADDR], env=env, capture_output=True, text=True)
        check("cli source etherscan single file", r.returncode == 0 and "A.sol" in r.stdout, r.stdout + r.stderr)
        r = subprocess.run(cli + ["txs", "base", ADDR, "-n", "5"], env=env, capture_output=True, text=True)
        check("cli txs", r.returncode == 0 and "0xcd" in r.stdout, r.stdout + r.stderr)
    finally:
        p.kill()
        logs = p.stdout.read().decode()
    seen.append(logs)
    check("no key in any answer, CLI output or log", not any(EKEY in x or BKEY in x for x in seen))

    # without the Blockscout key: the 12e behaviour
    p, base = start_service(tmp, es, bs, None)
    try:
        s, b = get(base, f"/q/base/source?address={ADDR}")
        check("no bkey: base is 402 not_on_plan as before", s == 402 and "not on the etherscan key" in b, b)
        s, b = get(base, f"/q/arbitrum/source?address={ADDR}")
        check("no bkey: arbitrum unverified answered by etherscan (empty source)",
              s == 200 and json.loads(b)["via"] == "etherscan", b)
    finally:
        p.kill()

    # a rejected Blockscout key
    p, base = start_service(tmp, es, bs, "proapi_BAD")
    try:
        s, b = get(base, f"/q/base/source?address={ADDR}")
        check("bad bkey: 503 tells the human, no key echoed", s == 503 and "blockscout" in b and "proapi_BAD" not in b, b)
        s, b = get(base, "/chains?probe=1")
        check("bad bkey: chains shows invalid_key", json.loads(b)["chains"]["base"]["blockscout"] == "invalid_key", b)
    finally:
        p.kill()

    print("ALL OK" if not failed else f"{failed} FAILED")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
