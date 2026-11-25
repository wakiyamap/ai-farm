#!/usr/bin/env python3
# Lead 94 fee-slot hunt, decisive sentinel experiment (run 60aaa..., 2026-11-09).
# Fork is still gen 357 with the proof13 prelude intact (no reset: fetch cache preserved).
# The settlement fee revert 0x3e9e7bf1(offered,required) is only visible in inner trace frames.
# required=1794573000 (aligned 300s timestamp-like), offered=1794572444 (blob fee field).
# Plan: for each candidate slot of the fee-module chain (MOD fee-getter slots {2,3,4,8,9,10,
# 11,12,18,20} + FOLIO timestamp slots {7,15,26,27,28}), set it to OFF and re-trace the
# settlement eth_call: if `required` flips away from 1794573000, the slot supplies required.
import json, subprocess, sys, os, time
WS = "/srv/farm/ws"
RESET = 26306742
FOLIO = "0x2cf4dafc17e163abd6770e1794e1ad10deb7d32e"
MOD = "0xa88cd6b934c64ea830b78967b2f8a0de91577edc"
SELL = "0x060505527c83e8bfeb9b4ff08248b82e688800f1"
BUY = "0xf404e5f887dbd5508e16a1198fcdd5de1a4296b8"
WINNER = "0xd98d34008d1bbb29013592c637f8e9fca4179fa0"
OWNER = "0x000000000000000000000000000000000000f007"
USDC = "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"
REQ = 1794573000
OFF = 1794572444
U = 9_057_578
SELL_AMT = 57582275034043643305
PAYFULL = 9398683583154130380  # proof11's payFull at settlement-era state (min_out/max_buy)
ENV = dict(os.environ, PATH="/opt/farm/bin:/opt/foundry/bin:" + os.environ.get("PATH", ""))

def sh(*cmd):
    r = subprocess.run(cmd, capture_output=True, text=True, env=ENV)
    if r.returncode != 0 or "FAILED" in r.stdout:
        sys.exit("FAILED %s: %s%s" % (cmd[:3], r.stdout[-200:], r.stderr[-200:]))
    return r.stdout.strip()

def rpc(method, params, timeout=240):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    import urllib.request
    req = urllib.request.Request("http://127.0.0.1:9003", data=body,
                                 headers={"content-type": "application/json"})
    out = json.loads(urllib.request.urlopen(req, timeout=timeout).read())
    if "error" in out:
        return out["error"]
    return out["result"]

def addr_word(a): return a[2:].lower().rjust(64, "0")
def w(v): return hex(v)[2:].zfill(64)

leg1 = open(WS + "/scratch/dtf92-swap1.txt").read().strip()
legf = open(WS + "/scratch/dtf92-swap2.txt").read().strip()
sel = sh("cast", "sig", "fundSwapAndBid(address,uint256,address,address,uint256,uint256,uint256,uint256,bytes,bytes,bytes,uint256)")
enc2 = sh("cast", "abi-encode", "f(address,uint256,address,address,uint256,uint256,uint256,uint256,bytes,bytes,bytes,uint256)",
          FOLIO, "8", SELL, BUY, str(U), str(PAYFULL), str(SELL_AMT), str(PAYFULL), legf, leg1, "0x", "0")
calldata = sel + enc2[2:]

def req_from_trace():
    res = rpc("debug_traceCall", [{"from": OWNER, "to": WINNER, "data": calldata}, "latest",
                                  {"tracer": "callTracer"}], timeout=240)
    if isinstance(res, dict):
        return ("ERR", str(res)[:200])
    found = []
    def walk(o):
        if isinstance(o, dict):
            rd = str(o.get("returnData") or "")
            if rd.startswith("0x3e9e7bf1"):
                found.append((int(rd[10:74], 16), int(rd[74:138], 16)))
            for v in o.values(): walk(v)
        elif isinstance(o, list):
            for x in o: walk(x)
    walk(res)
    return found

def setslot(addr, idx, val):
    return rpc("anvil_setStorageAt", [addr, "0x" + hex(idx)[2:], w(val)])

out = {"req_from": REQ, "off_from": OFF}
t0 = time.time()
# step 0: confirm the fee revert is live in the current state
out["trace0"] = req_from_trace()
print("trace0:", json.dumps(out["trace0"])[:300], "%.1fs" % (time.time() - t0)); sys.stdout.flush()

# step 1: read fee-module MOD slots 0-32 (fast: fetched by the reverted settlement)
mod_vals = {}
for i in range(33):
    v = int(rpc("eth_getStorageAt", [MOD, "0x" + hex(i)[2:], "latest"]), 16)
    if v: mod_vals[i] = str(v)
out["MOD_nonzero"] = mod_vals
print("MOD nonzero:", json.dumps(mod_vals)[:600]); sys.stdout.flush()

FOLIO_TS = {7: 0, 15: 0, 26: 0, 27: 0, 28: 0}  # will read actual values
for i in list(FOLIO_TS):
    FOLIO_TS[i] = int(rpc("eth_getStorageAt", [FOLIO, "0x" + hex(i)[2:], "latest"]), 16)
out["FOLIO_ts_slots"] = {str(k): str(v) for k, v in FOLIO_TS.items()}
print("FOLIO slots:", json.dumps(out["FOLIO_ts_slots"])[:400]); sys.stdout.flush()

def probe_required(tag):
    f = req_from_trace()
    out.setdefault("probes", []).append({"tag": tag, "found": f})
    print("probe", tag, "->", json.dumps(f)[:200], "%.1fs" % (time.time() - t0)); sys.stdout.flush()
    if f:
        return f[0][1]  # required
    return None

# step 2: single-slot sentinel: MOD fee-getter constants + any nonzero MOD slots
cands_mod = sorted(set([2, 3, 4, 8, 9, 10, 11, 12, 18, 20]) | {int(k) for k in mod_vals})
hit = None
for i in cands_mod:
    orig = int(rpc("eth_getStorageAt", [MOD, "0x" + hex(i)[2:], "latest"]), 16)
    setslot(MOD, i, OFF)
    rq = probe_required("MOD:%d" % i)
    if rq is None:
        hit = ("MOD", i, "no fee revert at all (fee check passed!)")
    elif rq != REQ:
        hit = ("MOD", i, "required flipped to %s" % rq)
    setslot(MOD, i, orig)
    if hit: break
    if time.time() - t0 > 480:
        out["budget"] = "single-slot budget spent"; break

# step 3: pairs if singles negative
if not hit and time.time() - t0 < 600:
    pairs = []
    for i in cands_mod:
        pairs += [(i, j) for j in cands_mod if j != i]
    for (i, j) in pairs:
        if time.time() - t0 > 600:
            out["budget"] = "pair budget spent"; break
        oi = int(rpc("eth_getStorageAt", [MOD, "0x" + hex(i)[2:], "latest"]), 16)
        oj = int(rpc("eth_getStorageAt", [MOD, "0x" + hex(j)[2:], "latest"]), 16)
        setslot(MOD, i, OFF); setslot(MOD, j, OFF)
        rq = probe_required("PAIR MOD:%d+MOD:%d" % (i, j))
        ok = (rq is None) or (rq != REQ)
        setslot(MOD, i, oi); setslot(MOD, j, oj)
        if ok:
            hit = ("MODpair", "%d+%d" % (i, j), "required %s" % rq)
            break

out["hit"] = hit
print("hit:", json.dumps(hit)[:300], "elapsed %.1fs" % (time.time() - t0))
json.dump(out, open(WS + "/scratch/rf-venue14.json", "w"), indent=1)
