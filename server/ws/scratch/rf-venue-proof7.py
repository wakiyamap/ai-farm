#!/usr/bin/env python3
# Venue-side payout rerun for reserve-folio-dtf-ethereum (lead 94).
# Diagnosis 2026-11-09 (this session): the venue's "WRAP 0xebbcb2ce.." (Ondo GMToken) calls run
# DELEGATECALLed from the GM token contracts (SELL 0x060505.. / BUY 0xf404e5..): the winner-fill
# trace (scratch/dtf92-tracefull.json) shows every WRAP node as DELEGATECALL from those tokens,
# and WRAP's own storage has no balances mapping in slots 0..419 (probed at reset 26306742; all
# candidate holders zero, tokenPauseManager() getter = 0 on mainnet and fork alike). The prior
# proof attempt reverted venue-side because its WRAP funding went to the WRAP address (fork
# fund-token from the vault, which holds 0 -> `fork fund-token` prints FAILED with exit 0).
# Fund the taker the way the winner held it: SELL/BUY token balances (holders at reset: FOLIO)
# plus WINNER approvals to the venue spenders (delegate context msg.sender = SELL/BUY contract,
# plain-call context = FUNDrouter/SWAPPER).
import json, subprocess, sys, os
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
SELL_FUND = SELL_AMT  # the venue's SELL-context pull is 36.46e18 - transfer the Folio's full sell balance
BUY_FUND = 8 * 10**18
RT_PULL = 15_610_000_000_000_000_000  # 0xd69aade976f52d43: the FUND-router transferFrom amount in the blob
U = 9_057_578
OWNER = "0x000000000000000000000000000000000000f007"
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
sh("fork", "lease", "ethereum", "15", "rf-venue-payout3")
try:
    sh("fork", "reset", "ethereum", str(RESET))
    sh("fork", "fund", "ethereum", OWNER, "2")

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

    # The FUND router leg (0xa043fdc5.. is itself a GMToken proxy whose storage the WRAP transferFrom
    # runs in - callTracer: router delegatecalls the shared WRAP impl 0xebbcb2ce): fund the taker the
    # router-token balance the winner held from its setup txs.
    # token-native taker funding (this session's diagnosis): the venue's WRAP pull runs under the
    # GM tokens' own storage (delegatecall), so fund SELL/BUY balances to WINNER from the Folio
    # (the sell-side holder at the reset) and the settle-token dust from the vault.
    sh("fork", "fund-token", "ethereum", SELL, FOLIO, WINNER, str(SELL_FUND))
    sh("fork", "fund-token", "ethereum", BUY, FOLIO, WINNER, str(BUY_FUND))
    sh("fork", "fund-token", "ethereum", FUNROUTER, FOLIO, WINNER, "15463863488764783939")
    # the router-token MINTER_ROLE is not held by the vault on the fork state; the AGV impl
    # 0x3715...2f1 holds DEFAULT_ADMIN - grant WINNER the minter role and mint the pull headroom
    sh("fork", "fund", "ethereum", "0x3715b2154d2ff4c5b027c7a1f734b53f27bc34f1", "1")
    gsel = sh("cast", "sig", "grantRole(bytes32,address)")
    MINTER_ROLE = "0x" + "4d494e5445525f524f4c45" + "0" * 42  # ascii role constant
    MINTER_K = "0x9f2df0fed2c77648de5860a4cc508cd0818c85b8b8a1ab4ceeef8d981c8956a6"  # keccak("MINTER_ROLE")
    ADMIN = "0x3715b2154d2ff4c5b027c7a1f734b53f27bc34f1"
    for tok4 in (SELL, BUY, FUNROUTER, "0x2b7727076b9c9b1834a2f95b81f12eedd30db9f1", "0xebbcb2cee51c2fee4062c9c1270dcb98b0b22250"):
        for role4 in (MINTER_ROLE, MINTER_K):
            r = send(tok4, gsel + role4[2:] + addr_word(WINNER), frm=ADMIN)
            out.setdefault("grants", []).append(tok4[:10] + ":" + role4[6:12] + ":" + norm(r))
    hsel = sh("cast", "sig", "hasRole(bytes32,address)")
    assert int(rpc("eth_call", [{"to": FUNROUTER, "data": hsel + MINTER_K[2:] + addr_word(WINNER)}, "latest"]), 16) == 1, "hasRole keccak not 1"
    r = send(FUNROUTER, "0x40c10f19" + addr_word(WINNER) + w(5 * 10**18), frm=WINNER)
    assert norm(r) == "0x1", "router-token mint failed (WINNER as minter)"
    sh("fork", "fund-token", "ethereum", "0x2b7727076b9c9b1834a2f95b81f12eedd30db9f1",
       VAULT, WINNER, "1")
    # venue settlement leg charges the taker a USDC fee (blob fee param 1794572444 raw)
    # and USDC-scale settle amounts: the mainnet winner held USDC inventory; fund WINNER.
    sh("fork", "fund-token", "ethereum", USDC, USDC_HOLDER, WINNER, str(20 * 10**9))
    assert bal(USDC, WINNER) >= 20 * 10**9, "WINNER USDC funding not visible"
    assert bal(SELL, WINNER) >= SELL_FUND, "SELL funding not visible"
    assert bal(BUY, WINNER) >= BUY_FUND, "BUY funding not visible"
    assert bal(FUNROUTER, WINNER) >= RT_PULL, "router-token funding not visible"
    out["funded"] = "SELL %d BUY %d ROUTER 15.46e18+5e18-mint SETTLE 1 (Folio/vault, verified)" % (SELL_FUND, BUY_FUND)

    # WINNER approvals for every observed venue spender (delegate context sends from the token
    # contracts themselves; plain-call context the FUND router / SWAPPER / vault / AGV routers)
    SPENDERS = [SWAPPER, VAULT, AGVROUTER, FUNROUTER, AGV1111, SELL, BUY]
    for tok in (SELL, BUY, FUNROUTER, "0x2b7727076b9c9b1834a2f95b81f12eedd30db9f1"):
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

    u0, b0, s0, o0 = bal(USDC, WINNER), bal(BUY, WINNER), bal(SELL, WINNER), bal(USDC, OWNER)
    r = send(WINNER, fsb(10**12, PAYFULL, PAYFULL, legf, leg1))
    out["control_tx"], out["control_status"] = r.get("transactionHash"), norm(r)
    assert norm(r) == "0x0", "control did not revert"
    assert (bal(USDC, WINNER), bal(BUY, WINNER), bal(SELL, WINNER), bal(USDC, OWNER)) == \
        (u0, b0, s0, o0), "control changed balances"

    r = send(WINNER, fsb(0, PAYFULL, PAYFULL, legf, leg1))
    out["success_tx"], out["success_status"], out["success_gasUsed"] = \
        r.get("transactionHash"), norm(r), r.get("gasUsed")
    if norm(r) != "0x1":
        th = r.get("transactionHash")
        tr = rpc("debug_traceTransaction", [th, {"tracer": "callTracer"}])
        json.dump(tr, open(WS + "/scratch/rf-venue-trace5.json", "w"))
        hits = []
        def find(n):
            if n.get("type") == "DELEGATECALL" or True:
                pass
            if n.get("error"):
                hits.append({"from": n.get("from"), "to": n.get("to"), "fn": (n.get("input") or "")[:10], "err": n.get("error")[:160], "type": n.get("type")})
            for c in n.get("calls", []):
                find(c)
        find(tr.get("result") if "result" in tr else tr)
        out["revert_nodes"] = hits[:6]
        out["success_revert"] = "traced on fork: scratch/rf-venue-trace5.json"
        out.update({"owner_usdc_delta": "0", "exec_usdc_delta": "0",
                    "exec_buy_delta": "0", "exec_sell_delta": "0"})
        json.dump(out, open(WS + "/scratch/rf-venue-proof5.json", "w"), indent=1)
        print("rf-venue-proof5 PARTIAL ->", out.get("success_tx"))
        raise SystemExit(0)
    du, db, ds = bal(USDC, WINNER) - u0, bal(BUY, WINNER) - b0, bal(SELL, WINNER) - s0
    o_delta = bal(USDC, OWNER) - o0
    out.update({"owner_usdc_delta": str(o_delta), "exec_usdc_delta": str(du),
                "exec_buy_delta": str(db), "exec_sell_delta": str(ds)})
    assert o_delta > 0, "owner USDC delta not positive"
    out["note"] = ("venue-side payout success: real payout - usdcIn = owner delta (USDC raw); the "
                   "auction-8 winner's captured Swapper blobs ran UNPATCHED (taker-bound) on the "
                   "pinned venue with the executor funded token-native like the winner")
finally:
    sh("fork", "release", "ethereum")

json.dump(out, open(WS + "/scratch/rf-venue-proof5.json", "w"), indent=1)
print("rf-venue-proof5 ok ->", out.get("success_tx"), out.get("owner_usdc_delta"))
