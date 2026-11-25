#!/usr/bin/env python3
# Lead 94 fee-slot hunt, scan take 2 (run a8e2e15e, 2026-11-09).
# Continuation of attempts 731/734: the settlement fee revert (custom error 0x3e9e7bf1
# (offered 1794572444, required 1794573000)) is INVARIANT to the settlement header timestamp,
# so the required side is forked-state storage fetched at reset 26306742. Prior scans covered
# CLONE/MOD/VAULT/CLONE_A/CLONE_B/AGVROUTER slots 0-63 and CLONE 6-1023 (negative).
# This scan: the remaining ranges named in lead 94 next_steps, plus FOLIO/FOLIOB which were
# never scanned (the Folio contract itself plausibly stores the fee parameter).
# Batch <=400 slots per pass (new slots trigger relay fetches; 400-slot batch ~40 s).
import json, subprocess, sys, os, time
WS = "/srv/farm/ws"
RESET = 26306742
FOLIO = "0x2cf4dafc17e163abd6770e1794e1ad10deb7d32e"
FOLIOB = "0xe592f69e4f60e9a78dba0043573b898386c01cb8"
SELL = "0x060505527c83e8bfeb9b4ff08248b82e688800f1"
BUY = "0xf404e5f887dbd5508e16a1198fcdd5de1a4296b8"
SWAPPER = "0x6131b5fae19ea4f9d964eac0408e4408b66337b5"
VAULT = "0x8f10b468b06c6fd214b65f87778827f7d113f996"
AGVROUTER = "0x111111125421ca6dc452d289314280a0f8842a65"
FUNROUTER = "0xA043FDc5A6E2E381e3532d5A97404b82fb7A0af8"
AGV1111 = "0x1111110f0f73c0b2ef09ec012eae758b3e03a902"
SETTLE = "0x2b7727076b9c9b1834a2f95b81f12eedd30db9f1"
WRAP = "0xebbcb2cee51c2fee4062c9c1270dcb98b0b22250"
REQ = 1794573000
OFF = 1794572444
TOL = 3000  # same tolerance the prior session used on slots 0-63
ENV = dict(os.environ, PATH="/opt/farm/bin:/opt/foundry/bin:" + os.environ.get("PATH", ""))

def sh(*cmd):
    r = subprocess.run(cmd, capture_output=True, text=True, env=ENV)
    if r.returncode != 0 or "FAILED" in r.stdout:
        sys.exit("FAILED %s: %s%s" % (cmd[:3], r.stdout[-300:], r.stderr[-300:]))
    return r.stdout.strip()

def rpc(method, params):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    import urllib.request
    req = urllib.request.Request("http://127.0.0.1:9003", data=body,
                                 headers={"content-type": "application/json"})
    for i in range(3):
        try:
            out = json.loads(urllib.request.urlopen(req, timeout=180).read())
            break
        except Exception as e:
            if i == 2:
                raise
            time.sleep(2)
    if "error" in out:
        sys.exit("RPC %s: %s" % (method, out["error"]))
    return out["result"]

def slot_val(addr, idx):
    return int(rpc("eth_getStorageAt", [addr, "0x" + hex(idx)[2:], "latest"]), 16)

def match(v):
    hits = []
    if v and abs(v - REQ) <= TOL:
        hits.append(("raw", v))
    for shift in (0, 32, 64, 96, 128, 160, 192, 224):
        low = (v >> shift) & 0xFFFFFFFF
        if low and abs(low - REQ) <= TOL:
            hits.append(("packed@%d" % shift, v))
    return hits

PLAN = [
    (FOLIO, 0, 255), (FOLIO, 256, 511), (FOLIO, 512, 767), (FOLIO, 768, 1023),
    (FOLIOB, 0, 255), (FOLIOB, 256, 511), (FOLIOB, 512, 767), (FOLIOB, 768, 1023),
    (VAULT, 64, 255), (VAULT, 256, 511), (VAULT, 512, 767), (VAULT, 768, 1023),
    (SELL, 0, 255), (SELL, 256, 511), (SELL, 512, 767), (SELL, 768, 1023),
    (BUY, 0, 255), (BUY, 256, 511), (BUY, 512, 767), (BUY, 768, 1023),
    (SETTLE, 0, 255), (SETTLE, 256, 511), (SETTLE, 512, 767), (SETTLE, 768, 1023),
    (WRAP, 0, 255), (WRAP, 256, 511), (WRAP, 512, 767), (WRAP, 768, 1023),
    (AGVROUTER, 64, 255), (AGVROUTER, 256, 511), (AGVROUTER, 512, 767), (AGVROUTER, 768, 1023),
    (AGV1111, 0, 255), (AGV1111, 256, 511), (AGV1111, 512, 767), (AGV1111, 768, 1023),
    (FUNROUTER, 0, 255), (FUNROUTER, 256, 511), (FUNROUTER, 512, 767), (FUNROUTER, 768, 1023),
]

sh("fork", "reset", "ethereum", str(RESET))
res = {"reset_block": RESET, "req": REQ, "off": OFF, "tol": TOL,
       "started": sh("date", "-u", "+%Y-%m-%dT%H:%M:%SZ")}
found = []
seen_nonzero = {}
t0 = time.time()
cur = None
scanned = 0
for addr, lo, hi in PLAN:
    if addr != cur:
        print("scanning %s slots %d-%d t=%.0fs" % (addr[:10], lo, hi, time.time() - t0), flush=True)
        cur = addr
    for s in range(lo, hi + 1):
        v = slot_val(addr, s)
        scanned += 1
        if v:
            seen_nonzero.setdefault(addr, []).append((s, str(v)))
        m = match(v)
        if m:
            found.append({"addr": addr, "slot": s, "value": str(v), "match": m[0][0]})
            print("HIT %s slot %d value %s %s" % (addr, s, v, m), flush=True)
            res["scanned"] = scanned
            res["found"] = found
            res["nonzero_seen"] = {a: lst[:24] for a, lst in seen_nonzero.items()}
            json.dump(res, open(WS + "/scratch/rf-venue-slotscan.json", "w"), indent=1)
            print("rf-venue-slotscan HIT after %d slots" % scanned, flush=True)
            sys.exit(0)
    # flush progress periodically
    res["scanned"] = scanned
    res["found"] = found
    res["nonzero_seen"] = {a: lst[:24] for a, lst in seen_nonzero.items()}
    json.dump(res, open(WS + "/scratch/rf-venue-slotscan.json", "w"), indent=1)

res["scanned"] = scanned
res["found"] = found
res["nonzero_seen"] = {a: lst[:24] for a, lst in seen_nonzero.items()}
res["complete"] = True
json.dump(res, open(WS + "/scratch/rf-venue-slotscan.json", "w"), indent=1)
print("rf-venue-slotscan done scanned=%d found=%d t=%.0fs" % (scanned, len(found), time.time() - t0))
