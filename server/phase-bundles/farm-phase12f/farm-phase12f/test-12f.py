#!/usr/bin/env python3
"""Offline tests for phase 12f: test-12f.py <farm-relayapi> <patched farm.nft>

A mock Relay API runs on a loopback port; nothing leaves this machine.
"""
import importlib.machinery
import importlib.util
import json
import sys
import threading
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

KEY = "testkey-ABC123xyz"
SEEN = []


class Mock(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def answer(self):
        n = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(n) if n else b""
        SEEN.append((self.command, self.path, self.headers.get("x-api-key"), body))
        if self.headers.get("x-api-key") != KEY:
            status, out = 401, {"message": "missing api key"}
        elif self.path.startswith("/requests/v3"):
            status, out = 200, {"requests": [], "echo": "your key is " + KEY}
        elif self.path.startswith("/quote"):
            status, out = 400, {"message": "no route", "sent": json.loads(body)}
        else:
            status, out = 200, {"path": self.path}
        data = json.dumps(out).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)
    do_GET = do_POST = answer


def load(path):
    loader = importlib.machinery.SourceFileLoader("farm_relayapi", path)
    spec = importlib.util.spec_from_loader("farm_relayapi", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def call(port, method, path, body=None):
    req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=body, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


def main():
    mod = load(sys.argv[1])
    nft = open(sys.argv[2], encoding="utf-8").read()
    mock = ThreadingHTTPServer(("127.0.0.1", 0), Mock)
    threading.Thread(target=mock.serve_forever, daemon=True).start()
    cfg = {"upstream": f"http://127.0.0.1:{mock.server_port}", "min_interval_s": 0, "daily_limit": 1000, "timeout_s": 5,
           "allow": {"GET": ["/chains", "/requests", "/intents/status", "/currencies", "/config", "/price"],
                     "POST": ["/quote", "/price", "/currencies"]}}
    mod.log = lambda **kw: LOGS.append(kw)
    api = mod.RelayApi(cfg, KEY)
    srv = ThreadingHTTPServer(("127.0.0.1", 0), mod.make_handler(api))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    p = srv.server_port
    results = []

    def t(name, cond):
        results.append(cond)
        print(f"  {'ok  ' if cond else 'FAIL'} {name}")

    s, b = call(p, "GET", "/chains")
    t("GET /chains is passed on with the key header", s == 200 and SEEN[-1][:3] == ("GET", "/chains", KEY))
    s, b = call(p, "GET", "/requests/v3?limit=1&user=0xabc")
    t("GET /requests/v3 keeps its query string", s == 200 and SEEN[-1][1] == "/requests/v3?limit=1&user=0xabc")
    t("the key is scrubbed from an answer that echoes it", KEY.encode() not in b and b"***" in b)
    s, b = call(p, "POST", "/quote/v2", json.dumps({"amount": "1"}).encode())
    t("POST /quote/v2 body reaches the upstream; its 400 comes back as 400",
      s == 400 and json.loads(b)["sent"] == {"amount": "1"})
    n = len(SEEN)
    for method, path, body in (("POST", "/execute/swap", b"{}"), ("POST", "/transactions/index", b"{}"),
                               ("POST", "/requests/v3", b"{}"), ("GET", "/quote/v2", None),
                               ("GET", "/chains/../execute", None), ("GET", "/requestsx", None),
                               ("GET", "/", None), ("POST", "/lives/intents", b"{}")):
        s, b = call(p, method, path, body)
        t(f"{method} {path} is refused (403) and never reaches the upstream", s == 403 and len(SEEN) == n)
    s, b = call(p, "POST", "/quote", b"not json")
    t("a POST body that is not JSON is refused (400)", s == 400 and len(SEEN) == n)
    s, b = call(p, "POST", "/quote", b"{" + b" " * 70000 + b"}")
    t("an oversized POST body is refused (413)", s == 413 and len(SEEN) == n)
    s, b = call(p, "DELETE", "/chains")
    t("DELETE is refused (405)", s == 405 and len(SEEN) == n)
    s, b = call(p, "GET", "/health")
    h = json.loads(b)
    t("/health reports counters and no key", s == 200 and h["ok"] and h["calls_today"] == 3 and KEY.encode() not in b)
    t("the key is in no log line", all(KEY not in json.dumps(x) for x in LOGS) and len(LOGS) >= 3)
    api.cfg["daily_limit"] = api.calls_today
    s, b = call(p, "GET", "/chains")
    t("the daily limit refuses with 429", s == 429 and len(SEEN) == n)
    api.cfg["daily_limit"] = 1000
    api.cfg["upstream"] = "http://127.0.0.1:1"
    s, b = call(p, "GET", "/chains")
    t("an unreachable upstream gives 502 without the key", s == 502 and KEY.encode() not in b)
    earner = [ln for ln in nft.splitlines() if "meta skuid earner" in ln and "tcp dport !=" in ln]
    t("farm.nft: the earner's allowed local ports include 29485", len(earner) == 1 and "29484, 29485 }" in earner[0])
    t("farm.nft: 29485 appears on no other rule", sum("29485" in ln for ln in nft.splitlines() if not ln.lstrip().startswith("#")) == 1)
    print(f"{sum(results)}/{len(results)} passed")
    sys.exit(0 if all(results) else 1)


LOGS = []
if __name__ == "__main__":
    main()
