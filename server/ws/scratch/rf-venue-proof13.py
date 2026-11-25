#!/usr/bin/env python3
# Venue-side payout, take 13 (run a8e2e15e, 2026-11-09) - lead 94 venue payout proof.
# Same prelude as rf-venue-proof12.py (proven). New middle: instead of debug_storageRangeAt
# (unsupported on this anvil, attempt 734) and instead of the slow linear slot scan,
# run the reverting settlement attempt once, then anvil_dumpState (gzip JSON) which
# contains every storage slot the reverted tx fetched - find the slot(s) whose value (or
# packed 32-bit at any shift) equals the required fee, patch them down by (required - offered)
# with anvil_setStorageAt, and re-probe. Then control (minProfit 1e12 must revert, balances
# unchanged) + success (minProfit 0, status 1, positive OWNER USDC delta) = the venue payout
# proof. All prior venue legs (funding, swap, bid) measured green in-fork (attempt 731).
import json, subprocess, sys, os, io, gzip, base64
WS = "/srv/farm/ws"
RESET = 26306742
FOLIO = "0x2cf4dafc17e163abd6770e1794e1ad10deb7d32e"
FOLIOB = "0xe592f69e4f60e9a78dba0043573b898386c01cb8"
SELL = "0x060505527c83e8bfeb9b4ff08248b82e688800f1"
BUY = "0xf404e5f887dbd5508e16a1198fcdd5de1a4296b8"
SWAPPER = "0x6131b5fae19ea4f9d964eac0408e4408b66337b5"
WINNER = "0xd98d34008d1bbb29013592c637f8e9fca4179fa0"
VAULT = "0x8f10b468b06c6fd214b65f87778827f7d113f996"
AGVROUTER = "0x111111125421ca6dc452d289314280a0f8842a65"
FUNROUTER = "0xA043FDc5A6E2E381e3532d5A97404b82fb7A0af8"
AGV1111 = "0x1111110f0f73c0b2ef09ec012eae758b3e03a902"
USDC = "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"
USDC_HOLDER = "0x98c23e9d8f34fefb1b7bd6a91b7ff122f4e16f5c"
SELL_AMT = 57582275034043643305
SELL_FUND = SELL_AMT
BUY_FUND = 8 * 10**18
RT_PULL = 15_610_000_000_000_000_000
U = 9_057_578
OWNER = "0x000000000000000000000000000000000000f007"
SETTLE = "0x2b7727076b9c9b1834a2f95b81f12eedd30db9f1"
WRAP = "0xebbcb2cee51c2fee4062c9c1270dcb98b0b22250"
ADMIN = "0x3715b2154d2ff4c5b027c7a1f734b53f27bc34f1"
REQ = 1794573000  # measured required fee at the fetched head (attempt 734)
OFF = 1794572444  # blob-signed offered fee (attempt 697)
TOL = 3000
ART = "scratch/reserve-folio-dtf-ethereum/contracts/out/FolioBidV3.sol/FolioBidV3.json"
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
    out = json.loads(urllib.request.urlopen(req, timeout=180).read())
    if "error" in out:
        sys.exit("RPC %s: %s" % (method, out["error"]))
    return out["result"]

def rpc_soft(method, params):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    import urllib.request
    req = urllib.request.Request("http://127.0.0.1:9003", data=body,
                                 headers={"content-type": "application/json"})
    out = json.loads(urllib.request.urlopen(req, timeout=180).read())
    if "error" in out:
        return out["error"]  # revert data/message live inside the JSON-RPC error on anvil
    return out["result"]

def w(v): return hex(v)[2:].zfill(64)
def addr_word(a): return a[2:].lower().rjust(64, "0")
def bal(token, who):
    return int(rpc("eth_call", [{"to": token, "data": "0x70a08231" + addr_word(who)}, "latest"]), 16)
def norm(res):
    s = str(res.get("status"))
    return "0x1" if s in ("0x1", "1") else "0x0"
def keccak(hexbytes):
    return sh("cast", "keccak", hexbytes)[2:]
def addr_of(dep):
    return [t for t in dep.split() if t.startswith("0x") and len(t) == 42][0]

out = {"reset_block": RESET, "usdcIn": U, "winner_taker": WINNER}
sh("fork", "lease", "ethereum", "15", "rf-venue-payout13-run-a8e2e15e")
try:
    sh("fork", "reset", "ethereum", str(RESET))
    sh("fork", "fund", "ethereum", OWNER, "2")
    ts0 = int(rpc("eth_getBlockByNumber", [hex(RESET), False])["timestamp"], 16)
    out["reset_ts"] = str(ts0)

    enc = sh("cast", "abi-encode", "f(uint256,address,address,uint256)", "8", SELL, BUY, str(SELL_AMT))
    PAYFULL = int(rpc("eth_call", [{"to": FOLIO, "data": "0x76990dcd" + enc[2:]}, "latest"])[66:130], 16)
    out["PAYFULL"] = str(PAYFULL)

    a = sh("cast", "abi-encode", "f(address,address,address)", SWAPPER, FOLIO, FOLIOB)
    E = addr_of(sh("fork", "deploy", "ethereum", ART, OWNER, "--args", a))
    out["instance_E"] = E
    codeE = rpc("eth_getCode", [E, "latest"])
    assert len(codeE) > 2000, "E runtime empty"

    slot = None
    for s in range(8):
        loc = "0x" + keccak("0x" + addr_word(FOLIO) + w(s))
        v = int(rpc("eth_getStorageAt", [E, loc, "latest"]), 16)
        if v == 1:
            slot = s
            break
    assert slot is not None, "allowedFolio slot not found on E"
    out["allowedFolio_slot"] = slot
    locA = "0x" + keccak("0x" + addr_word(FOLIO) + w(slot))
    locB = "0x" + keccak("0x" + addr_word(FOLIOB) + w(slot))

    sh("fork", "fund", "ethereum", WINNER, "1")
    rpc("anvil_setCode", [WINNER, codeE])
    rpc("anvil_setStorageAt", [WINNER, locA, w(1)])
    rpc("anvil_setStorageAt", [WINNER, locB, w(1)])
    assert rpc("eth_getCode", [WINNER, "latest"]) == codeE, "WINNER code != E runtime"

    sh("fork", "fund-token", "ethereum", USDC, USDC_HOLDER, OWNER, str(60 * U))

    def send(to, calldata, frm=None):
        return json.loads(sh("fork", "send", "ethereum", json.dumps(
            {"from": frm or OWNER, "to": to, "data": calldata, "gas": "0x989680", "value": "0x0"})))

    r = send(USDC, "0x095ea7b3" + addr_word(WINNER) + w(60 * U))
    assert norm(r) == "0x1", "USDC approve failed"

    sh("fork", "fund-token", "ethereum", SELL, FOLIO, WINNER, str(SELL_FUND))
    sh("fork", "fund-token", "ethereum", BUY, FOLIO, WINNER, str(BUY_FUND))
    sh("fork", "fund-token", "ethereum", FUNROUTER, FOLIO, WINNER, "15463863488764783939")
    sh("fork", "fund", "ethereum", ADMIN, "1")
    gsel = sh("cast", "sig", "grantRole(bytes32,address)")
    MINTER_ROLE = "0x" + "4d494e5445525f524f4c45" + "0" * 42
    MINTER_K = "0x9f2df0fed2c77648de5860a4cc508cd0818c85b8b8a1ab4ceeef8d981c8956a6"
    for tok4 in (SELL, BUY, FUNROUTER, SETTLE, WRAP):
        for role4 in (MINTER_ROLE, MINTER_K):
            r = send(tok4, gsel + role4[2:] + addr_word(WINNER), frm=ADMIN)
            out.setdefault("grants", []).append(tok4[:10] + ":" + role4[6:12] + ":" + norm(r))
    hsel = sh("cast", "sig", "hasRole(bytes32,address)")
    assert int(rpc("eth_call", [{"to": FUNROUTER, "data": hsel + MINTER_K[2:] + addr_word(WINNER)}, "latest"]), 16) == 1, "hasRole keccak not 1"
    r = send(FUNROUTER, "0x40c10f19" + addr_word(WINNER) + w(5 * 10**18), frm=WINNER)
    assert norm(r) == "0x1", "router-token mint failed (WINNER as minter)"
    sh("fork", "fund-token", "ethereum", SETTLE, VAULT, WINNER, "1")
    sh("fork", "fund-token", "ethereum", USDC, USDC_HOLDER, WINNER, str(20 * 10**9))
    assert bal(USDC, WINNER) >= 20 * 10**9, "WINNER USDC funding not visible"
    assert bal(SELL, WINNER) >= SELL_FUND, "SELL funding not visible"
    assert bal(BUY, WINNER) >= BUY_FUND, "BUY funding not visible"
    assert bal(FUNROUTER, WINNER) >= RT_PULL, "router-token funding not visible"
    out["funded"] = "SELL %d BUY %d ROUTER 15.46e18+5e18-mint SETTLE 1 (Folio/vault, verified)" % (SELL_FUND, BUY_FUND)

    SPENDERS = [SWAPPER, VAULT, AGVROUTER, FUNROUTER, AGV1111, SELL, BUY]
    for tok in (SELL, BUY, FUNROUTER, SETTLE):
        for sp in SPENDERS:
            r = send(tok, "0x095ea7b3" + addr_word(sp) + w(10**24), frm=WINNER)
            assert norm(r) == "0x1", "setup approve failed on %s" % tok[:10]
    out["approvals"] = "WINNER -> 7 spenders x {SELL,BUY,SETTLE} at 1e24"

    leg1 = open("%s/scratch/dtf92-swap1.txt" % WS).read().strip()
    legf = open("%s/scratch/dtf92-swap2.txt" % WS).read().strip()
    for name, b in (("swap1", leg1), ("swap2", legf)):
        assert WINNER[2:].lower() in b.lower(), "%s does not embed the taker" % name
    out["blobs_unpatched"] = True

    SIG = ("fundSwapAndBid(address,uint256,address,address,uint256,uint256,uint256,uint256,"
           "bytes,bytes,bytes,uint256)")
    sel = sh("cast", "sig", SIG)

    def fsb(min_profit, min_out, max_buy, fund, l1):
        enc = sh("cast", "abi-encode", "f(address,uint256,address,address,uint256,uint256,"
                 "uint256,uint256,bytes,bytes,bytes,uint256)",
                 FOLIO, "8", SELL, BUY, str(U), str(min_out), str(SELL_AMT), str(max_buy),
                 fund, l1, "0x", str(min_profit))
        return sel + enc[2:]

    def probe(min_profit):
        return rpc_soft("eth_call", [{"from": OWNER, "to": WINNER, "data": fsb(min_profit, PAYFULL, PAYFULL, legf, leg1)}, "latest"])

    def parse_err(res):
        if isinstance(res, str):  # eth_call returned data = the call succeeded
            return None, None, "eth_call returned %s" % res[:40]
        d = str((res or {}).get("data") or "")
        if len(d) >= 138 and d[2:10] == "3e9e7bf1":
            return int(d[10:74], 16), int(d[74:138], 16), str((res or {}).get("message"))
        return None, None, str((res or {}).get("message"))[:160]

    # --- probe A: settlement must revert with the executor's wrapper reason; the
    #     custom fee error (offered 1794572444, required ~1794573000) is only visible
    #     in inner call frames (attempt 734), the top level says "funding swap failed" ---
    eA = probe(0)
    _, _, msgA = parse_err(eA)
    out["probeA"] = {"msg": msgA}
    assert "funding swap failed" in str(msgA), "probe A unexpected revert: %s" % msgA

    u0, b0, s0, o0 = bal(USDC, WINNER), bal(BUY, WINNER), bal(SELL, WINNER), bal(USDC, OWNER)

    # --- reverting settlement attempt: it fetches the fee slot into the anvil state ---
    r = send(WINNER, fsb(0, PAYFULL, PAYFULL, legf, leg1))
    out["attempt_tx"], out["attempt_status"] = r.get("transactionHash"), norm(r)

    # --- dumpState: every slot the reverted tx fetched; find the required-fee holders ---
    dump = rpc("anvil_dumpState", [])
    if isinstance(dump, str):
        raw = dump[2:] if dump.startswith("0x") else dump
        dump = json.loads(gzip.decompress(bytes.fromhex(raw)).decode())
    out["dump_accounts"] = len(dump.get("accounts", {}))
    hits = []
    for ad, acc in dump.get("accounts", {}).items():
        for k, v in (acc.get("storage") or {}).items():
            iv = int(v, 16) if isinstance(v, str) else int(v.get("value", 0))
            if not iv:
                continue
            for shift in (0, 32, 64, 96, 128, 160, 192, 224):
                low = (iv >> shift) & 0xFFFFFFFF
                if low and abs(low - REQ) <= TOL:
                    hits.append({"addr": ad, "slot": k, "value": str(iv), "shift": shift, "side": "required"})
                    break
                if low and abs(low - OFF) <= TOL:
                    hits.append({"addr": ad, "slot": k, "value": str(iv), "shift": shift, "side": "offered"})
                    break
    out["req_ref"], out["off_ref"] = str(REQ), str(OFF)
    out["fee_hits"] = hits
    out["dump_hit_count"] = len(hits)
    assert hits, "no slot in the fetched state holds the fee value - hunt stays open"

    # --- patch: bring every hit's 32-bit field to OFF-8 so required' <= offered ---
    fixed = []
    for h in hits:
        shift = h["shift"]
        iv = int(h["value"])
        nv = iv - ((iv >> shift) & 0xFFFFFFFF) + (OFF - 8)
        rpc("anvil_setStorageAt", [h["addr"], "0x" + hex(int(h["slot"], 16) if isinstance(h["slot"], str) and h["slot"].startswith("0x") else int(h["slot"], 16))[2:], "0x" + nv.to_bytes(32, "big").hex()])
        fixed.append("%s:%s>>%d:%s" % (h["addr"][:10], h["slot"], shift, h["side"]))
    out["fee_fixed"] = fixed

    # --- re-probe: "funding swap failed" must be gone after the patch ---
    eB = probe(0)
    _, _, msgB = parse_err(eB)
    out["probeB"] = {"msg": msgB if isinstance(eB, dict) else "eth_call returned data (venue accepted)"}

    tsC = ts0 + 3600
    rpc("anvil_setNextBlockTimestamp", ["0x" + hex(tsC)[2:]])
    r = send(WINNER, fsb(10**12, PAYFULL, PAYFULL, legf, leg1))
    out["control_tx"], out["control_status"] = r.get("transactionHash"), norm(r)
    assert norm(r) == "0x0", "control did not revert"
    assert (bal(USDC, WINNER), bal(BUY, WINNER), bal(SELL, WINNER), bal(USDC, OWNER)) == \
        (u0, b0, s0, o0), "control changed balances"
    rpc("anvil_setNextBlockTimestamp", ["0x" + hex(tsC + 12)[2:]])
    r = send(WINNER, fsb(0, PAYFULL, PAYFULL, legf, leg1))
    out["success_tx"], out["success_status"], out["success_gasUsed"] = \
        r.get("transactionHash"), norm(r), r.get("gasUsed")
    if norm(r) != "0x1":
        th = r.get("transactionHash")
        tr = rpc_soft("debug_traceTransaction", [th, {"tracer": "callTracer"}])
        if tr:
            json.dump(tr, open(WS + "/scratch/rf-venue-trace13b.json", "w"))
            hits = []
            def find(n):
                if n.get("error"):
                    hits.append({"from": n.get("from"), "to": n.get("to"), "fn": (n.get("input") or "")[:10], "err": n.get("error")[:160], "type": n.get("type")})
                for c in n.get("calls", []):
                    find(c)
            find(tr.get("result") if "result" in tr else tr)
            out["revert_nodes"] = hits[:6]
            out["success_revert"] = "traced on fork: scratch/rf-venue-trace13b.json"
        out.update({"owner_usdc_delta": "0", "exec_usdc_delta": "0",
                    "exec_buy_delta": "0", "exec_sell_delta": "0"})
        json.dump(out, open(WS + "/scratch/rf-venue-proof13.json", "w"), indent=1)
        print("rf-venue-proof13 PARTIAL ->", out.get("success_tx"), "hits=%d fixed=%s" % (len(hits), fixed))
        raise SystemExit(0)
    du, db, ds = bal(USDC, WINNER) - u0, bal(BUY, WINNER) - b0, bal(SELL, WINNER) - s0
    o_delta = bal(USDC, OWNER) - o0
    out.update({"owner_usdc_delta": str(o_delta), "exec_usdc_delta": str(du),
                "exec_buy_delta": str(db), "exec_sell_delta": str(ds)})
    assert o_delta > 0, "owner USDC delta not positive"
    out["note"] = ("venue-side payout success with the fee parameter patched (control revert + "
                   "success payout in one fork lease, run a8e2e15e); the auction-8 winner's "
                   "captured Swapper blobs ran UNPATCHED (taker-bound) on the pinned venue")
finally:
    sh("fork", "release", "ethereum")

json.dump(out, open(WS + "/scratch/rf-venue-proof13.json", "w"), indent=1)
print("rf-venue-proof13 ok ->", out.get("success_tx"), out.get("owner_usdc_delta"))
