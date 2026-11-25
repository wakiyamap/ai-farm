#!/usr/bin/env python3
"""Offline tests for phase 16a: test-16a.py <rpc-relay> <scout-enum> <context-scout> <scout.md> <candidates-dir>

No network: the relay's upstream calls are replaced by a fake that records the URL."""
import importlib.machinery
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import threading
import urllib.request

sys.dont_write_bytecode = True
relay_p, enum_p, ctx_p, md_p, cand_d =[os.path.realpath(a) for a in sys.argv[1:6]]
fails = []


def check(name, cond):
    print(f"  {'ok' if cond else 'FAIL'}: {name}")
    if not cond:
        fails.append(name)


# ---------- rpc-relay ----------
loader = importlib.machinery.SourceFileLoader("rpc_relay_16a", relay_p)
spec = importlib.util.spec_from_loader(loader.name, loader)
rr = importlib.util.module_from_spec(spec)
loader.exec_module(rr)
rr.DB_PATH = os.path.join(tempfile.mkdtemp(), "ops.db")

calls = []


class FakeResp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def fake_urlopen(req, timeout=None):
    body = json.loads(req.data)
    calls.append((req.full_url, body["method"], body.get("params")))
    if body["method"] == "getLatestLedger":
        res = {"id": "x", "protocolVersion": 23, "sequence": 60000000}
    elif body["method"] == "eth_blockNumber":
        res = "0x10"
    elif body["method"] == "eth_sendRawTransaction":
        res = "0x" + "ab" * 32
    else:
        res = {"events": []}
    return FakeResp(json.dumps({"jsonrpc": "2.0", "id": 1, "result": res}).encode())


rr.urllib.request.urlopen = fake_urlopen
config = {
    "alchemy_daily_cu": {"live": 100, "paper": 100, "research": 1000, "fork": 100, "scout": 1000, "watch": 100},
    "chains": {"base": {"alchemy": "base-mainnet", "public": ["https://mainnet.base.org"]}},
    "nonevm_chains": {"stellar": {"alchemy": "stellar-mainnet", "public": [], "kind": "stellar",
                                  "lanes": ["research", "scout", "paper"]}},
    "lane_by_user": {"earner": "scout"},
}
relay = rr.Relay(config, "KEY")


def call(chain, lane, method, params=None, allow_send=False):
    calls.clear()
    return relay.call(chain, lane, method, params if params is not None else {}, 7, allow_send=allow_send)


r = call("stellar", "research", "getLatestLedger")
check("stellar getLatestLedger (research) answered", r.get("result", {}).get("sequence") == 60000000)
check("stellar goes to Alchemy's stellar-mainnet URL", calls and calls[0][0] == "https://stellar-mainnet.g.alchemy.com/v2/<REDACTED>")
check("stellar empty params are left out (Stellar RPC refuses [])", calls and calls[0][2] is None)
r = call("stellar", "research", "getLatestLedger", [])
check("stellar params [] (the relay's default) are left out too", "result" in r and calls[0][2] is None)
check("stellar CU counted (10 per getLatestLedger, 2 calls)", relay.stats.alchemy_cu_today("research") == 20)
r = call("stellar", "scout", "getEvents", {"startLedger": 1, "filters": []})
check("stellar getEvents (scout) answered, object params passed", "result" in r and calls[0][2] == {"startLedger": 1, "filters": []})
r = call("stellar", "research", "sendTransaction", {"transaction": "AAAA"})
check("stellar sendTransaction refused, nothing upstream", r.get("error", {}).get("code") == -32601 and not calls)
r = call("stellar", "research", "eth_sendRawTransaction", ["0x00"], allow_send=True)
check("eth_sendRawTransaction to stellar on the send socket refused", "error" in r and not calls)
r = call("stellar", "research", "sendTransaction", {"transaction": "AAAA"}, allow_send=True)
check("sendTransaction on the send socket refused", "error" in r and not calls)
r = call("stellar", "live", "getLatestLedger")
check("stellar on the live lane refused", "error" in r and not calls)
r = call("stellar", "fork", "getLatestLedger")
check("stellar on the fork lane refused", "error" in r and not calls)
r = call("stellar", "research", "eth_call", [{}, "latest"])
check("eth_call on stellar refused", "error" in r and not calls)
r = call("base", "research", "getEvents", {})
check("getEvents on base refused (EVM list unchanged)", r.get("error", {}).get("code") == -32601 and not calls)
r = call("base", "research", "eth_blockNumber", [])
check("base eth_blockNumber still answered via public first", r.get("result") == "0x10" and calls[0][0] == "https://mainnet.base.org")
r = call("base", "live", "eth_sendRawTransaction", ["0x02"], allow_send=True)
check("base public send still goes to Alchemy only", calls and calls[0][0] == "https://base-mainnet.g.alchemy.com/v2/<REDACTED>")
check("relay.chains has both, nonevm only stellar", set(relay.chains) == {"base", "stellar"} and set(relay.nonevm) == {"stellar"})

# HTTP: /health and POST /stellar
rr.Handler.relay = relay
srv = rr.Server(("127.0.0.1", 0), rr.Handler)
threading.Thread(target=srv.serve_forever, daemon=True).start()
port = srv.server_address[1]
h = json.load(urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=5)) if False else None
# urlopen is faked for upstream; use a raw socket client for our own server
import http.client
c = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
relay._cycle = (1e18, {"stub": True})
c.request("GET", "/health")
h = json.loads(c.getresponse().read())
check("/health chains stay EVM-only", h.get("chains") == ["base"])
check("/health lists nonevm_chains", h.get("nonevm_chains") == ["stellar"])
c.request("POST", "/stellar?lane=research", body=json.dumps({"jsonrpc": "2.0", "id": 3, "method": "getLatestLedger"}),
          headers={"Content-Type": "application/json"})
p = json.loads(c.getresponse().read())
check("POST /stellar over HTTP answered", p.get("result", {}).get("sequence") == 60000000 and p.get("id") == 3)
srv.shutdown()

# ---------- scout-enum ----------
t = tempfile.mkdtemp()
open(f"{t}/kb", "w").write("#!/usr/bin/env python3\nimport sys\nsys.exit(0)\n")
open(f"{t}/ledger", "w").write("#!/bin/sh\nexit 0\n")
os.chmod(f"{t}/kb", 0o755)
os.chmod(f"{t}/ledger", 0o755)
json.dump([{"slug": "blend", "name": "Blend", "category": "Lending", "chainTvls": {"Stellar": 1e8}, "listedAt": 1700000000},
           {"slug": "tiny-stellar", "name": "Tiny", "category": "Dexs", "chainTvls": {"Stellar": 1000}},
           {"slug": "some-dex", "name": "Some Dex", "category": "Dexs", "chainTvls": {"Base": 60000}, "listedAt": 1790000000}],
          open(f"{t}/llama.json", "w"))
env = dict(os.environ, SCOUT_WS=f"{t}/ws", KB_BIN=f"{t}/kb", LEDGER_BIN=f"{t}/ledger", LLAMA_FILE=f"{t}/llama.json")
out = subprocess.run([sys.executable, "-I", enum_p], env=env, capture_output=True, text=True)
q = sorted(os.listdir(f"{t}/ws/scout/queue"))
check("scout-enum ran", out.returncode == 0)
check("stellar protocol queued at tier 2, before base (tier 3)",
      len(q) == 2 and q[0].startswith("2-") and "protocol-stellar-blend" in q[0] and q[1].startswith("3-"))
check("stellar below MIN_TVL skipped", not any("tiny" in f for f in q))

# ---------- context-scout ----------
for f in os.listdir(f"{t}/ws/scout/queue"):
    os.remove(f"{t}/ws/scout/queue/{f}")
import shutil
for f in os.listdir(cand_d):
    shutil.copy(f"{cand_d}/{f}", f"{t}/ws/scout/queue/{f}")
json.dump({"id": "protocol-stellar-blend", "kind": "protocol", "tier": 2, "age": 5, "chain": "stellar", "slug": "blend"},
          open(f"{t}/ws/scout/queue/2-00005-protocol-stellar-blend.json", "w"))
outs = []
for i in range(3):
    o = subprocess.run([sys.executable, "-I", ctx_p], env=dict(env, FARM_RUN_ID=f"r{i}"), capture_output=True, text=True)
    outs.append(o.stdout + o.stderr)
check("targeted candidate 1 first: Blend interest auctions", "candidate id: stellar-blend-interest-auction" in outs[0]
      and "interest auctions" in outs[0])
check("targeted candidate 2 second: BIM", "candidate id: stellar-bim-harvest" in outs[1])
check("stellar protocol gets the Stellar steps, formatted",
      "Stellar is not EVM" in outs[2] and "projects/blend/index.js" in outs[2] and '{"type":"contract"' in outs[2]
      and "eth_getCode" not in outs[2])

# ---------- scout.md ----------
md = open(md_p, encoding="utf-8").read()
check("scout.md has the Stellar section before 'What to write'",
      md.index("## Stellar (16a, read only)") < md.index("## What to write"))

print("all tests passed" if not fails else f"TESTS FAILED: {len(fails)}")
sys.exit(1 if fails else 0)
