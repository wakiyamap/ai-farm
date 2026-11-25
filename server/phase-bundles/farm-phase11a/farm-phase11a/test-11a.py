#!/usr/bin/env python3
"""Phase 11a offline tests: farm-feed against a fake WebSocket upstream on localhost (no chain, no key).

  test-11a.py <farm-feed>
"""
import base64
import hashlib
import importlib.machinery
import importlib.util
import json
import socket
import struct
import sys
import threading
import time
import urllib.error
import urllib.request

sys.dont_write_bytecode = True
if len(sys.argv) != 2:
    sys.exit(__doc__)
FEED = sys.argv[1]
SECRET = "<REDACTED>"
RESULTS = []
ADDR = "0x" + "ab" * 20
ADDR2 = "0x" + "cd" * 20
T0 = "0x" + "11" * 32


def load():
    name = f"farmfeed_{time.time_ns()}"
    loader = importlib.machinery.SourceFileLoader(name, FEED)
    mod = importlib.util.module_from_spec(importlib.util.spec_from_loader(name, loader))
    loader.exec_module(mod)
    mod.say = lambda msg: None
    return mod


def frame(op, payload, fin=True):
    n = len(payload)
    head = bytes([(0x80 if fin else 0) | op])
    if n < 126:
        head += bytes([n])
    elif n < 65536:
        head += bytes([126]) + struct.pack("!H", n)
    else:
        head += bytes([127]) + struct.pack("!Q", n)
    return head + payload


class Upstream:
    """A WebSocket JSON-RPC server that confirms subscriptions and lets the test push notifications."""

    def __init__(self, refuse=False, sub_error=None):
        self.refuse, self.sub_error = refuse, sub_error
        self.srv = socket.socket()
        self.srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.srv.bind(("127.0.0.1", 0))
        self.srv.listen(8)
        self.port = self.srv.getsockname()[1]
        self.url = f"ws://127.0.0.1:{self.port}/v2/{SECRET}"
        self.lock = threading.Lock()
        self.conns, self.received, self.subs = [], [], {}
        self.accepts = self.pongs = self.unsubs = self.masked_ok = 0
        self.n = 0
        threading.Thread(target=self.accept, daemon=True).start()

    def accept(self):
        while True:
            try:
                c, _ = self.srv.accept()
            except OSError:
                return
            threading.Thread(target=self.serve, args=(c,), daemon=True).start()

    def serve(self, c):
        try:
            buf = b""
            while b"\r\n\r\n" not in buf:
                d = c.recv(4096)
                if not d:
                    return
                buf += d
            head, _, buf = buf.partition(b"\r\n\r\n")
            with self.lock:
                self.accepts += 1
            if self.refuse:
                c.sendall(f"HTTP/1.1 401 Unauthorized key {SECRET}\r\nContent-Length: 0\r\n\r\n".encode())
                c.close()
                return
            key = [ln.split(":", 1)[1].strip() for ln in head.decode().split("\r\n")
                   if ln.lower().startswith("sec-websocket-key")][0]
            acc = base64.b64encode(hashlib.sha1((key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode()).digest()).decode()
            c.sendall(f"HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
                      f"Sec-WebSocket-Accept: {acc}\r\n\r\n".encode())
            with self.lock:
                self.conns.append(c)
            while True:
                while True:
                    f = self.parse(buf)
                    if f:
                        break
                    d = c.recv(65536)
                    if not d:
                        return
                    buf += d
                op, payload, buf = f
                if op == 0x9:
                    c.sendall(frame(0xA, payload))
                elif op == 0xA:
                    with self.lock:
                        self.pongs += 1
                elif op == 0x8:
                    return
                elif op == 0x1:
                    self.on_json(c, json.loads(payload))
        except OSError:
            pass
        finally:
            with self.lock:
                if c in self.conns:
                    self.conns.remove(c)
                for sid in [s for s, v in self.subs.items() if v[0] is c]:
                    del self.subs[sid]
            try:
                c.close()
            except OSError:
                pass

    def parse(self, buf):
        if len(buf) < 2:
            return None
        op, n, off = buf[0] & 0x0F, buf[1] & 0x7F, 2
        assert buf[1] & 0x80, "client frames must be masked"
        if n == 126:
            if len(buf) < 4:
                return None
            n, off = struct.unpack("!H", buf[2:4])[0], 4
        elif n == 127:
            if len(buf) < 10:
                return None
            n, off = struct.unpack("!Q", buf[2:10])[0], 10
        if len(buf) < off + 4 + n:
            return None
        mask = buf[off:off + 4]
        payload = bytes(b ^ mask[i & 3] for i, b in enumerate(buf[off + 4:off + 4 + n]))
        with self.lock:
            self.masked_ok += 1
        return op, payload, buf[off + 4 + n:]

    def on_json(self, c, m):
        with self.lock:
            self.received.append(m)
            if m["method"] == "eth_subscribe":
                if self.sub_error:
                    out = {"jsonrpc": "2.0", "id": m["id"], "error": {"code": -32000, "message": self.sub_error}}
                else:
                    self.n += 1
                    sid = f"0xsub{self.n}"
                    self.subs[sid] = (c, m["params"])
                    out = {"jsonrpc": "2.0", "id": m["id"], "result": sid}
            elif m["method"] == "eth_unsubscribe":
                self.unsubs += 1
                self.subs.pop(m["params"][0], None)
                out = {"jsonrpc": "2.0", "id": m["id"], "result": True}
            else:
                out = {"jsonrpc": "2.0", "id": m["id"], "result": "0x1"}
        c.sendall(frame(0x1, json.dumps(out).encode()))

    def sub(self, kind, limit=5.0):
        end = time.monotonic() + limit
        while time.monotonic() < end:
            with self.lock:
                for sid, (c, params) in self.subs.items():
                    if params[0] == kind:
                        return sid, c, params
            time.sleep(0.02)
        raise AssertionError(f"upstream never saw an eth_subscribe {kind}")

    def push(self, kind, result, fragmented=False, pad=0):
        sid, c, _ = self.sub(kind)
        if pad:
            result = dict(result, pad="x" * pad)
        raw = json.dumps({"jsonrpc": "2.0", "method": "eth_subscription",
                          "params": {"subscription": sid, "result": result}}).encode()
        if fragmented:
            cut = len(raw) // 2
            c.sendall(frame(0x1, raw[:cut], fin=False) + frame(0x9, b"hi") + frame(0x0, raw[cut:]))
        else:
            c.sendall(frame(0x1, raw))
        return len(raw)

    def drop(self):
        with self.lock:
            conns = list(self.conns)
        for c in conns:
            try:
                c.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass

    def close(self):
        self.srv.close()
        self.drop()


def head(n):
    return {"number": hex(n), "hash": "0x" + f"{n:064x}", "parentHash": "0x" + f"{n - 1:064x}",
            "timestamp": hex(1700000000 + 12 * n), "baseFeePerGas": "0x3b9aca00", "logsBloom": "0x" + "00" * 256}


def log(i, addr=ADDR):
    return {"address": addr, "topics": [T0], "data": "0x" + f"{i:064x}", "blockNumber": hex(100 + i),
            "transactionHash": "0x" + f"{i:064x}", "logIndex": "0x0", "removed": False}


class Rig:
    def __init__(self, ups, **cfg):
        self.mod = load()
        self.feed = self.mod.Feed(cfg, {name: u.url for name, u in ups.items()}, SECRET)
        handler = type("H", (self.mod.Handler,), {"feed": self.feed})
        self.http = self.mod.Server(("127.0.0.1", 0), handler)
        self.port = self.http.server_port
        threading.Thread(target=self.http.serve_forever, daemon=True).start()

    def get(self, path, timeout=10):
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{self.port}{path}", timeout=timeout) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    def bg(self, path):
        box = {}
        t = threading.Thread(target=lambda: box.update(r=self.get(path)), daemon=True)
        t.start()
        return t, box

    def close(self):
        self.http.shutdown()
        self.http.server_close()


def case(name):
    def deco(fn):
        def run():
            ups = []
            try:
                fn(ups)
                RESULTS.append((name, True, ""))
            except Exception as exc:                       # noqa: BLE001
                RESULTS.append((name, False, f"{type(exc).__name__}: {exc}"))
            finally:
                for u in ups:
                    u.close()
        run.__name__ = "run"
        return run
    return deco


def up(ups, **kw):
    u = Upstream(**kw)
    ups.append(u)
    return u


LOGS = f"/logs/ethereum?address={ADDR}&topic0={T0}"


@case("/head returns the pushed head; with after= it waits for a higher one; a quiet chain times out")
def t_head(ups):
    u = up(ups)
    r = Rig({"ethereum": u})
    t, box = r.bg("/head/ethereum?timeout=5")
    u.push("newHeads", head(100))
    t.join(6)
    code, b = box["r"]
    assert code == 200 and b["number"] == 100 and b["timestamp"] == 1700001200 and "age_ms" in b, b
    t0 = time.monotonic()
    t, box = r.bg("/head/ethereum?after=100&timeout=5")
    time.sleep(0.4)
    assert "r" not in box, "returned before a new head existed"
    u.push("newHeads", head(101))
    t.join(6)
    assert box["r"][1]["number"] == 101 and time.monotonic() - t0 < 3, box
    code, b = r.get("/head/ethereum?after=101&timeout=0.5")
    assert code == 200 and b.get("timeout") is True and b["number"] == 101, b
    assert len([m for m in u.received if m["method"] == "eth_subscribe"]) == 1, "one upstream subscription for all callers"
    r.close()


@case("/head is refused (400) on a chain that is not in the heads list, without opening a connection")
def t_head_not_offered(ups):
    u = up(ups)
    r = Rig({"ethereum": up(ups), "elysium": u})
    code, b = r.get("/head/elysium?timeout=1")
    assert code == 400 and "not offered" in b["error"], (code, b)
    assert u.accepts == 0, "connected upstream for a refused request"
    code, b = r.get("/head/nochain")
    assert code == 404, (code, b)
    r.close()


@case("/logs subscribes with the address list and topics, then delivers logs in order with a moving cursor")
def t_logs(ups):
    u = up(ups)
    r = Rig({"ethereum": u})
    code, b = r.get(f"/logs/ethereum?address={ADDR2},{ADDR.upper().replace('0X', '0x')}&topic0={T0}&timeout=5")
    assert code == 200 and b["logs"] == [] and "." in b["cursor"], (code, b)
    _, _, params = u.sub("logs")
    assert params[1] == {"address": sorted([ADDR, ADDR2]), "topics": [T0]}, params
    cur = b["cursor"]
    path = f"/logs/ethereum?address={ADDR},{ADDR2}&topic0={T0}"
    t, box = r.bg(f"{path}&after={cur}&timeout=5")
    time.sleep(0.3)
    assert "r" not in box, "returned before a log existed"
    u.push("logs", log(1))
    t.join(6)
    code, b = box["r"]
    assert code == 200 and [x["data"] for x in b["logs"]] == [log(1)["data"]] and not b.get("gap"), b
    u.push("logs", log(2))
    u.push("logs", log(3))
    time.sleep(0.3)
    code, b2 = r.get(f"{path}&after={b['cursor']}&timeout=5")
    assert [x["data"] for x in b2["logs"]] == [log(2)["data"], log(3)["data"]], b2
    code, b3 = r.get(f"{path}&after={b2['cursor']}&timeout=0.4")
    assert b3.get("timeout") is True and b3["logs"] == [] and b3["cursor"] == b2["cursor"], b3
    assert len([m for m in u.received if m["method"] == "eth_subscribe"]) == 1, "same filter, one subscription"
    r.close()


@case("after the upstream drops the connection the feed resubscribes and the old cursor gets gap: true")
def t_reconnect(ups):
    u = up(ups)
    r = Rig({"ethereum": u})
    cur = r.get(LOGS + "&timeout=5")[1]["cursor"]
    u.push("logs", log(1))
    b = r.get(f"{LOGS}&after={cur}&timeout=5")[1]
    assert len(b["logs"]) == 1, b
    t, box = r.bg(f"{LOGS}&after={b['cursor']}&timeout=8")
    time.sleep(0.2)
    u.drop()
    t.join(9)
    code, g = box["r"]
    assert code == 200 and g.get("gap") is True and g["logs"] == [] and g["cursor"] != b["cursor"], (code, g)
    assert u.accepts == 2, f"connections: {u.accepts}"
    u.push("logs", log(7))
    b = r.get(f"{LOGS}&after={g['cursor']}&timeout=5")[1]
    assert [x["data"] for x in b["logs"]] == [log(7)["data"]] and not b.get("gap"), b
    r.close()


@case("a subscription nobody polls is unsubscribed and the connection closed (no cost when unused)")
def t_idle(ups):
    u = up(ups)
    r = Rig({"ethereum": u}, idle_unsubscribe_s=0.6)
    r.get(LOGS + "&timeout=5")
    r.get("/head/ethereum?timeout=0.2")
    end = time.monotonic() + 6
    while time.monotonic() < end and (u.conns or u.unsubs < 2):
        time.sleep(0.1)
    assert u.unsubs == 2 and not u.conns, f"unsubscribes {u.unsubs}, connections open {len(u.conns)}"
    h = r.get("/health")[1]
    assert h["chains"]["ethereum"]["status"] == "idle" and h["chains"]["ethereum"]["subscriptions"] == [], h
    code, b = r.get(LOGS + "&timeout=5")
    assert code == 200 and u.accepts == 2, "a new poll must connect again"
    r.close()


@case("the daily CU budget stops everything: 429, subscriptions dropped, connection closed")
def t_budget(ups):
    u = up(ups)
    r = Rig({"ethereum": u}, daily_cu_budget=30)          # 750 bytes
    assert r.get("/head/ethereum?timeout=0.2")[0] == 200
    t, box = r.bg("/head/ethereum?after=5&timeout=6")
    time.sleep(0.2)
    u.push("newHeads", head(1), pad=900)
    t.join(7)
    assert box["r"][0] == 429 and "budget" in box["r"][1]["error"], box
    code, b = r.get(LOGS + "&timeout=1")
    assert code == 429 and "budget" in b["error"], (code, b)
    end = time.monotonic() + 4
    while time.monotonic() < end and u.conns:
        time.sleep(0.1)
    h = r.get("/health")[1]
    assert h["exhausted"] is True and not u.conns and h["cu_today"] > 30, h
    with r.feed.cond:                                      # next UTC day: the feed works again
        r.feed.day = r.feed.exhausted_day = "2000-01-01"
    assert r.get("/head/ethereum?timeout=0.2")[0] == 200
    assert r.get("/health")[1]["exhausted"] is False
    r.close()


@case("a log filter over its own daily cap is dropped for the day; the head stream goes on")
def t_filter_cap(ups):
    u = up(ups)
    r = Rig({"ethereum": u}, per_filter_daily_cu=20)       # 500 bytes
    cur = r.get(LOGS + "&timeout=5")[1]["cursor"]
    r.get("/head/ethereum?timeout=0.2")
    t, box = r.bg(f"{LOGS}&after={cur}&timeout=6")
    time.sleep(0.2)
    u.push("logs", log(1), pad=700)
    t.join(7)
    assert box["r"][0] == 429 and "cap" in box["r"][1]["error"], box
    code, b = r.get(LOGS + "&timeout=1")
    assert code == 429 and "cap" in b["error"], (code, b)
    u.push("newHeads", head(50))
    code, b = r.get("/head/ethereum?timeout=3")
    assert code == 200 and b["number"] == 50, (code, b)
    code, b = r.get(f"/logs/ethereum?address={ADDR2}&topic0={T0}&timeout=3")
    assert code == 200, "another filter must still work"
    r.close()


@case("bad requests are refused before anything is subscribed (address, topic0, sizes, filter count)")
def t_validation(ups):
    u = up(ups)
    r = Rig({"ethereum": u}, max_log_filters_per_chain=2, max_addresses_per_filter=2)
    for path in (f"/logs/ethereum?topic0={T0}", f"/logs/ethereum?address=0x1234&topic0={T0}",
                 f"/logs/ethereum?address={ADDR}", f"/logs/ethereum?address={ADDR}&topic0=0xdead",
                 f"/logs/ethereum?address={ADDR},{ADDR2},{'0x' + 'ef' * 20}&topic0={T0}",
                 f"{LOGS}&after=nonsense", "/head/ethereum?after=x", "/head/ethereum?timeout=soon"):
        code, b = r.get(path)
        assert code == 400 and b.get("error"), (path, code, b)
    assert u.accepts == 0, "a refused request reached the upstream"
    for i in range(2):
        assert r.get(f"/logs/ethereum?address={'0x' + f'{i:040x}'}&topic0={T0}&timeout=3")[0] == 200
    code, b = r.get(f"/logs/ethereum?address={ADDR}&topic0={T0}&timeout=1")
    assert code == 429 and "log filters" in b["error"], (code, b)
    r.close()


@case("fragmented messages, a ping in the middle and a 70 kB frame are read correctly; frames we send are masked")
def t_frames(ups):
    u = up(ups)
    r = Rig({"ethereum": u})
    cur = r.get(LOGS + "&timeout=5")[1]["cursor"]
    u.push("logs", log(1), fragmented=True)
    u.push("logs", log(2), pad=70000)
    time.sleep(0.4)
    b = r.get(f"{LOGS}&after={cur}&timeout=5")[1]
    assert [x["data"] for x in b["logs"]] == [log(1)["data"], log(2)["data"]] and len(b["logs"][1]["pad"]) == 70000, \
        [x["data"] for x in b["logs"]]
    end = time.monotonic() + 3
    while time.monotonic() < end and not u.pongs:
        time.sleep(0.05)
    assert u.pongs >= 1 and u.masked_ok >= 2, f"pongs {u.pongs}"
    r.close()


@case("an upstream that refuses the connection or the subscription gives 503, and the key never leaks")
def t_errors(ups):
    r = Rig({"ethereum": up(ups, refuse=True), "base": up(ups, sub_error=f"nope {SECRET}")}, heads=["ethereum", "base"])
    code, b = r.get("/head/ethereum?timeout=6")
    assert code == 503 and "down" in b["error"], (code, b)
    code, b2 = r.get("/head/base?timeout=6")
    assert code == 503 and "refused" in b2["error"], (code, b2)
    h = r.get("/health")[1]
    blob = json.dumps([b, b2, h])
    assert SECRET not in blob and "<key>" in blob, blob[:300]
    r.close()


@case("a cursor older than the buffer gets gap: true instead of a silent hole")
def t_overrun(ups):
    u = up(ups)
    r = Rig({"ethereum": u}, buffer_logs=3)
    cur = r.get(LOGS + "&timeout=5")[1]["cursor"]
    for i in range(1, 6):
        u.push("logs", log(i))
    time.sleep(0.4)
    b = r.get(f"{LOGS}&after={cur}&timeout=2")[1]
    assert b.get("gap") is True and b["logs"] == [], b
    b = r.get(f"{LOGS}&after={b['cursor']}&timeout=0.3")[1]
    assert b.get("timeout") is True, b
    r.close()


@case("--check reads one head and reports its size; a dead endpoint exits 1 without the key in the output")
def t_check(ups):
    import contextlib
    import io
    u = up(ups)
    mod = load()
    threading.Thread(target=lambda: (u.sub("newHeads"), u.push("newHeads", head(9))), daemon=True).start()
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        rc = mod.check("ethereum", u.url, SECRET, limit=5)
        rc2 = mod.check("ethereum", up(ups, refuse=True).url, SECRET, limit=2)
    assert rc == 0 and "head 9" in out.getvalue() and "CU per head" in out.getvalue(), out.getvalue()
    assert rc2 == 1 and "FAILED" in err.getvalue() and SECRET not in err.getvalue(), err.getvalue()


for fn in list(globals().values()):
    if callable(fn) and getattr(fn, "__name__", "") == "run":
        fn()

print("== phase 11a")
for name, ok, why in RESULTS:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"\n        {why}" if why else ""))
failed = [r for r in RESULTS if not r[1]]
print("ALL PASS" if not failed else f"{len(failed)} FAILED")
sys.exit(1 if failed else 0)
