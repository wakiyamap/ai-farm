#!/usr/bin/env python3
"""Offline tests for phase 12b (no network, no keys, nothing outside a temp directory).

  test-12b.py <rpc-relay> <farm-signer> [--lib DIR] [--old]

--lib DIR  where farmchains.py is (default /opt/farm/lib)
--old      the files are the unpatched ones: failures are expected, report only (exit 0)
"""
import io
import json
import os
import sys
import tempfile
import threading
import types
import urllib.error
import urllib.request

args = [a for a in sys.argv[1:] if not a.startswith("--")]
OLD = "--old" in sys.argv
LIB = sys.argv[sys.argv.index("--lib") + 1] if "--lib" in sys.argv else "/opt/farm/lib"
if "--lib" in sys.argv:
    args.remove(LIB)
RELAY_PATH, SIGNER_PATH = args[0], args[1]
TMP = tempfile.mkdtemp(prefix="t12b-")
PRIV = "https://private.example/fast"
results = []


def case(name, fn):
    try:
        fn()
        results.append((name, None))
    except Exception as exc:                      # noqa: BLE001
        results.append((name, f"{type(exc).__name__}: {exc}"))


# ---------------------------------------------------------------- relay
def load(path, name, extra=None):
    ns = {"__name__": name, "__file__": path}
    ns.update(extra or {})
    exec(compile(open(path, encoding="utf-8").read(), path, "exec"), ns)   # noqa: S102
    return ns


class FakeResp:
    def __init__(self, body):
        self.body = json.dumps(body).encode()

    def read(self, n=-1):
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class Net:
    """Stands in for urllib.request.urlopen; records every URL asked."""

    def __init__(self):
        self.urls, self.answers = [], {}

    def __call__(self, req, timeout=None):
        url = req.full_url if hasattr(req, "full_url") else req
        self.urls.append(url)
        for part, ans in self.answers.items():
            if part in url:
                if isinstance(ans, Exception):
                    raise ans
                return FakeResp(ans)
        return FakeResp({"jsonrpc": "2.0", "id": 1, "result": "0x" + "ab" * 32})


R = load(RELAY_PATH, "relay12b")
R["DB_PATH"] = os.path.join(TMP, "no-such.db")
real_urlopen = urllib.request.urlopen


def relay(private=True):
    cfg = {"chains": {"ethereum": {"alchemy": "eth-mainnet", "public": ["https://public.example/eth"]},
                      "base": {"alchemy": "base-mainnet", "public": ["https://public.example/base"]}},
           "alchemy_daily_cu": {"live": 10**9, "paper": 10**9, "research": 10**9}}
    if private:
        cfg["private_send"] = {"ethereum": PRIV}
    net = Net()
    urllib.request.urlopen = net
    return R["Relay"](cfg, "KEY"), net


SEND = ("eth_sendRawTransaction", ["0x02aa"])


def t_public_send_unchanged():
    r, net = relay()
    out = r.call("ethereum", "live", *SEND, 7, allow_send=True)
    assert "result" in out and out["id"] == 7, out
    assert len(net.urls) == 1 and "g.alchemy.com" in net.urls[0], net.urls


def t_private_send_goes_private_only():
    r, net = relay()
    out = r.call("ethereum", "live", *SEND, 7, allow_send=True, route="private")
    assert "result" in out, out
    assert net.urls == [PRIV], net.urls


def t_private_no_route_on_chain():
    r, net = relay()
    out = r.call("base", "live", *SEND, 7, allow_send=True, route="private")
    assert "error" in out and "no private send route" in out["error"]["message"], out
    assert net.urls == [], net.urls


def t_private_not_configured():
    r, net = relay(private=False)
    out = r.call("ethereum", "live", *SEND, 7, allow_send=True, route="private")
    assert "error" in out and net.urls == [], (out, net.urls)


def t_private_failure_never_falls_back():
    r, net = relay()
    net.answers["private.example"] = urllib.error.URLError("down")
    out = r.call("ethereum", "live", *SEND, 7, allow_send=True, route="private")
    assert "error" in out, out
    assert net.urls == [PRIV], net.urls                      # Alchemy and public nodes never asked
    r2, net2 = relay()
    net2.answers["private.example"] = {"jsonrpc": "2.0", "id": 1, "error": {"code": -32601, "message": "method not found"}}
    out = r2.call("ethereum", "live", *SEND, 7, allow_send=True, route="private")
    assert "error" in out and net2.urls == [PRIV], (out, net2.urls)


def t_private_needs_send_socket():
    r, net = relay()
    out = r.call("ethereum", "live", *SEND, 7, allow_send=False, route="private")
    assert "error" in out and "not allowed" in out["error"]["message"], out
    assert net.urls == [], net.urls


def t_unknown_route_refused():
    r, net = relay()
    out = r.call("ethereum", "live", *SEND, 7, allow_send=True, route="mempool")
    assert "error" in out and net.urls == [], (out, net.urls)


def t_reads_ignore_route():
    r, net = relay()
    out = r.call("ethereum", "live", "eth_getBalance", ["0x" + "11" * 20, "latest"], 7, allow_send=True, route="private")
    assert "result" in out and PRIV not in net.urls, (out, net.urls)


for f in (t_public_send_unchanged, t_private_send_goes_private_only, t_private_no_route_on_chain,
          t_private_not_configured, t_private_failure_never_falls_back, t_private_needs_send_socket,
          t_unknown_route_refused, t_reads_ignore_route):
    case("relay: " + f.__name__[2:], f)
urllib.request.urlopen = real_urlopen

# ---------------------------------------------------------------- signer
fk = types.ModuleType("farmkeys")
fk.selector = lambda sig: "0x" + format(abs(hash(sig)) % (16 ** 8), "08x")
fk.load_master = lambda: b"m"
fk.derive_private_key = lambda master, name: b"k"
fk.address_of = lambda priv: "0x" + "bb" * 20
fk.checksum = lambda a: a
fk.sign_eip1559 = lambda priv, tx: b"\x02\xaa"
sys.modules["farmkeys"] = fk
sys.path.insert(0, LIB)
S = load(SIGNER_PATH, "signer12b")
LIVE = os.path.join(TMP, "live")
S["LIVE_DIR"], S["STATE"], S["LOG"] = LIVE, TMP, os.path.join(TMP, "signer.log")
ALLOWED = "0x" + "aa" * 20


class FakeRpc:
    def __init__(self, fail=False):
        self.sends, self.fail = [], fail

    def call(self, chain, method, params, lane="live", route="(not passed)"):
        if method == "eth_getTransactionCount":
            return "0x5"
        if method == "eth_sendRawTransaction":
            self.sends.append((chain, route))
            if self.fail:
                raise RuntimeError("all providers failed: private: down")
            return "0x" + "cd" * 32
        return "0x0"


class FakePrices:
    disabled = {}

    def eth_usd(self, chain):
        return 2000.0


def signer(send_route=None, cfg_extra=None, fail=False):
    os.makedirs(f"{LIVE}/botA/state", exist_ok=True)
    lines = ["id: botA", "chains: [ethereum, base]", "capital_usd: 16", f"allowed_contracts: [\"{ALLOWED}\"]"]
    if send_route is not None:
        lines.append(f"send_route: {send_route}")
    open(f"{LIVE}/botA/manifest.yaml", "w").write("\n".join(lines) + "\n")
    for p in (S["LOG"], os.path.join(TMP, "spend.json")):
        if os.path.exists(p):
            os.unlink(p)
    s = S["Signer"].__new__(S["Signer"])
    s.cfg = dict({"max_loss_per_tx_usd": 50, "relay_url": "http://x", "usdc": {}}, **(cfg_extra or {}))
    s.master, s.rpc, s.prices = b"m", FakeRpc(fail), FakePrices()
    s.lock, s.spend_path = threading.Lock(), os.path.join(TMP, "spend.json")
    S["Signer"].caller_bot = staticmethod(lambda conn: ("botA", 1000))
    return s


def req(chain="ethereum", to=ALLOWED):
    return {"op": "send", "chain": chain, "to": to, "data": "0x", "value": "0x0",
            "gas": hex(200000), "maxFeePerGas": hex(10**9), "maxPriorityFeePerGas": hex(10**8)}


def lastlog():
    return json.loads(open(S["LOG"]).read().strip().splitlines()[-1])


def t_private_manifest_ethereum():
    s = signer("private")
    out = s.handle(None, req())
    assert out.get("ok") and out.get("route") == "private", out
    assert s.rpc.sends == [("ethereum", "private")], s.rpc.sends
    rec = lastlog()
    assert rec["decision"] == "sent" and rec["route"] == "private" and rec["nonce"] == 5, rec


def t_private_manifest_other_chain_is_public():
    s = signer("private")
    out = s.handle(None, req("base"))
    assert out.get("ok") and out.get("route") == "public", out
    assert s.rpc.sends == [("base", None)], s.rpc.sends
    assert lastlog()["route"] == "public"


def t_no_send_route_is_public():
    s = signer(None)
    out = s.handle(None, req())
    assert out.get("ok") and s.rpc.sends == [("ethereum", None)], (out, s.rpc.sends)
    assert lastlog()["route"] == "public"


def t_quoted_value_and_case():
    s = signer('"Private"')
    out = s.handle(None, req())
    assert out.get("ok") and s.rpc.sends == [("ethereum", "private")], (out, s.rpc.sends)


def t_bad_send_route_rejected():
    s = signer("privte")
    out = s.handle(None, req())
    assert not out.get("ok") and "send_route" in out["error"], out
    assert s.rpc.sends == [] and lastlog()["decision"] == "reject"


def t_private_chains_from_config():
    s = signer("private", {"private_send_chains": []})
    out = s.handle(None, req())
    assert out.get("ok") and s.rpc.sends == [("ethereum", None)], (out, s.rpc.sends)


def t_policy_still_applies():
    s = signer("private")
    out = s.handle(None, req(to="0x" + "ee" * 20))
    assert not out.get("ok") and "allowed_contracts" in out["error"], out
    assert s.rpc.sends == []
    big = dict(req(), gas=hex(3_000_000), maxFeePerGas=hex(10**11))       # 600 USD worst case
    out = s.handle(None, big)
    assert not out.get("ok") and "exceeds L" in out["error"], out


def t_broadcast_failed_logged_with_route():
    s = signer("private", fail=True)
    out = s.handle(None, req())
    assert not out.get("ok") and "broadcast failed" in out["error"], out
    rec = lastlog()
    assert rec["decision"] == "broadcast_failed" and rec["route"] == "private" and rec["nonce"] == 5, rec


def t_rpc_path_carries_route():
    seen = []
    rpc = S["Rpc"]("http://x")
    rpc._unix = lambda path, body: seen.append(path) or {"result": "0x1"}
    rpc.call("ethereum", "eth_sendRawTransaction", ["0x02"], route="private")
    rpc.call("ethereum", "eth_sendRawTransaction", ["0x02"])
    assert seen == ["/ethereum?lane=live&route=private", "/ethereum?lane=live"], seen


for f in (t_private_manifest_ethereum, t_private_manifest_other_chain_is_public, t_no_send_route_is_public,
          t_quoted_value_and_case, t_bad_send_route_rejected, t_private_chains_from_config,
          t_policy_still_applies, t_broadcast_failed_logged_with_route, t_rpc_path_carries_route):
    case("signer: " + f.__name__[2:], f)

bad = [r for r in results if r[1]]
for name, err in results:
    print(f"  {'FAIL' if err else 'ok  '} {name}" + (f"  ({err})" if err else ""))
print(f"{len(results) - len(bad)} of {len(results)} passed" + (" (old files: failures expected)" if OLD else ""))
sys.exit(0 if OLD or not bad else 1)
