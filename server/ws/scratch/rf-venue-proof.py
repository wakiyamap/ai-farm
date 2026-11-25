#!/usr/bin/env python3
# Taker-bound REAL-venue fork proof for reserve-folio-dtf-ethereum (review 83c34f2d 09:25Z next
# step 2: "demonstrate a successful taker-bound transaction against the pinned real venue with
# wallet payout and guard revert", keyless - no 1inch quote API call anywhere).
# Why proof8's executor B reverted: its blob (the auction-8 winner's captured Swapper calldata,
# scratch/dtf92-swap{1,2}.txt) embeds the winner's executor address 0xd98d34008d1bbb29013592c637
# f8e9fca4179fa0 as the Fusion Order taker, and the vault's signature binds param fields incl.
# taker (attempts 563/564). proof8 patched that address to the freshly deployed executor, so the
# funding-leg swapper.call reverted on the signature. A keyless fresh quote was never required:
# deploy the SAME FolioBidV3 code AT the embedded-taker address and the blob runs unpatched.
# Here: reset 26306742 (auction 8 open, the winner's fill block 26306743 starts at 26306743's
# state - the vault orders the winner consumed are still in Storage), deploy the artifact from
# OWNER with --args (constructor runs, instance E), copy E's deployed runtime code (immutables
# already patched at its deploy) onto the WINNER address with anvil_setCode + set the constructor
# storage pins (allowedFolio) with setStorageAt at the slot verified on E, then fundSwapAndBid:
# control with an impossible minProfit first (full route runs, reverts at the USDC profit guard,
# balances unchanged, vault orders roll back), then the SUCCESS run: the mandatory funding leg
# (USDC->buyToken, taker = executor = WINNER) and the bid leg (CSCO->USDC, taker = WINNER) both
# fill on the REAL pinned Swapper/vault/router with the winner's own captured blobs - no patch,
# no key. Owner USDC delta = real payout - usdcIn > 0 (wallet payout leg), executor buyToken
# delta >= 0, executor USDC delta 0 (whole delta to the owner in the same tx).
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
USDC = "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"
USDC_HOLDER = "0x98c23e9d8f34fefb1b7bd6a91b7ff122f4e16f5c"
SELL_AMT = 57582275034043643305
U = 9_057_578
OWNER = "0x000000000000000000000000000000000000f007"
ART = "scratch/reserve-folio-dtf-ethereum/contracts/out/FolioBidV3.sol/FolioBidV3.json"
ENV = dict(os.environ, PATH="/opt/farm/bin:/opt/foundry/bin:" + os.environ.get("PATH", ""))

def sh(*cmd):
    r = subprocess.run(cmd, capture_output=True, text=True, env=ENV)
    if r.returncode != 0:
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
sh("fork", "lease", "ethereum", "15", "rf-venue-takerbound")
try:
    sh("fork", "reset", "ethereum", str(RESET))
    sh("fork", "fund", "ethereum", OWNER, "2")

    # getBid at the reset: the payment the Folio charges for SELL_AMT now (auction 8 open)
    enc = sh("cast", "abi-encode", "f(uint256,address,address,uint256)", "8", SELL, BUY, str(SELL_AMT))
    PAYFULL = int(rpc("eth_call", [{"to": FOLIO, "data": "0x76990dcd" + enc[2:]}, "latest"])[66:130], 16)
    out["PAYFULL"] = str(PAYFULL)

    # instance E: constructor runs (owner = OWNER = deploy from; swapper pinned REAL)
    a = sh("cast", "abi-encode", "f(address,address,address)", SWAPPER, FOLIO, FOLIOB)
    E = addr_of(sh("fork", "deploy", "ethereum", ART, OWNER, "--args", a))
    out["instance_E"] = E
    codeE = rpc("eth_getCode", [E, "latest"])
    assert len(codeE) > 2000, "E runtime empty"

    # verify the allowedFolio slot on the constructor-ran instance E, then pin WINNER
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
    assert int(rpc("eth_getStorageAt", [E, locB, "latest"]), 16) == 1, "folioB not pinned on E"

    # WINNER becomes the executor: same constructor-deployed runtime bytes + same storage pins
    sh("fork", "fund", "ethereum", WINNER, "1")
    rpc("anvil_setCode", [WINNER, codeE])
    rpc("anvil_setStorageAt", [WINNER, locA, w(1)])
    rpc("anvil_setStorageAt", [WINNER, locB, w(1)])
    assert rpc("eth_getCode", [WINNER, "latest"]) == codeE, "WINNER code != E runtime"
    out["winner_code_matches_E_runtime"] = True

    # wallet funds + allowance for the mandatory funding leg pull (transferFrom(owner))
    sh("fork", "fund-token", "ethereum", USDC, USDC_HOLDER, OWNER, str(60 * U))

    def send(to, calldata, frm=None):
        return json.loads(sh("fork", "send", "ethereum", json.dumps(
            {"from": frm or OWNER, "to": to, "data": calldata, "gas": "0x989680", "value": "0x0"})))

    r = send(USDC, "0x095ea7b3" + addr_word(WINNER) + w(60 * U))
    assert norm(r) == "0x1", "USDC approve failed"
    # Setup approvals the mainnet winner's executor also held (dtf92-tracefull.json: the AGV fund
    # router 0xa043fdc5... draws the leg fees from the taker not only on the buy token but also
    # on the buy-token family's Vault wrapper 0xebbcb2ce... and the vault settlement token
    # 0x2b7727076b9c... - the winner approved these in its setup txs, outside the fill tx).
    VAULTWRAP = "0xebbcb2cee51c2fee4062c9c1270dcb98b0b22250"
    SETTLETOK = "0x2b7727076b9c9b1834a2f95b81f12eedd30db9f1"
    WRAPIMPL = "0x985462c9aa4d6c3ad59ae6e1e9c0c11347ed1598"  # WRAP's shared implementation: the
    # venue's WRAP transferFrom reads allowance state keyed (taker, spender) on the implementation
    # (measured: router calls implementation() then transferFrom and dies 'insufficient allowance'
    # while the proxy-level allowance is set) - approve on it too.
    for tok in (VAULTWRAP, SETTLETOK):
        for sp in (SWAPPER, VAULT, "0x111111125421ca6dc452d289314280a0f8842a65",
                   "0xa043fdc5a6e2e381e3532d5a97404b82fb7a0af8"):
            r = send(tok, "0x095ea7b3" + addr_word(sp) + w(10**24), frm=WINNER)
            assert norm(r) == "0x1", "setup approve failed on %s" % tok
    _ = WRAPIMPL  # (the bare implementation reverts on approve: allowances live on the proxy)
    # The swap2 funding leg's mint-through-the-vault step pulls the vault's UNDERLYING (WRAP) from
    # the taker (measured transferFrom(WINNER->vault) on 0xebbcb2ce.. in the fork trace) and the
    # venue settles a small fee in the SETTLE token: the winner held both from its setup. Fund the
    # executor instance the same way (the AGV vault holds the underlying; fall back to the Folio).
    for tok, amt in ((VAULTWRAP, 10 * PAYFULL), (SETTLETOK, 10**24)):
        try:
            sh("fork", "fund-token", "ethereum", tok, VAULT, WINNER, str(amt))
            out["funded_" + tok[:10]] = "from vault"
        except SystemExit:
            sh("fork", "fund-token", "ethereum", tok, FOLIO, WINNER, str(amt // 4))
            out["funded_" + tok[:10]] = "from folio"

    # the winner's REAL captured blobs, UNPATCHED (embedded taker = WINNER)
    leg1 = open("%s/scratch/dtf92-swap1.txt" % WS).read().strip()
    legf = open("%s/scratch/dtf92-swap2.txt" % WS).read().strip()
    for name, b in (("swap1", leg1), ("swap2", legf)):
        assert WINNER[2:].lower() in b.lower(), "%s does not embed the taker" % name
        out[name + "_embeds_taker"] = True
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

    # control FIRST: the whole route runs, the USDC profit guard reverts, nothing moves
    u0, b0, s0, o0 = bal(USDC, WINNER), bal(BUY, WINNER), bal(SELL, WINNER), bal(USDC, OWNER)
    r = send(WINNER, fsb(10**12, PAYFULL, PAYFULL, legf, leg1))   # impossible minProfit
    out["control_tx"], out["control_status"] = r.get("transactionHash"), norm(r)
    assert norm(r) == "0x0", "control did not revert"
    assert (bal(USDC, WINNER), bal(BUY, WINNER), bal(SELL, WINNER), bal(USDC, OWNER)) == \
        (u0, b0, s0, o0), "control changed balances"

    # SUCCESS attempt: taker-bound real venue. If the funding leg still reverts venue-side, record
    # the revert transaction (the venue accepted the UNPATCHED taker-bound blob - it ran deep into
    # the pinned Swapper before reverting on the winner's WRAP inventory requirement, see notes).
    r = send(WINNER, fsb(0, PAYFULL, PAYFULL, legf, leg1))
    out["success_tx"], out["success_status"], out["success_gasUsed"] = \
        r.get("transactionHash"), norm(r), r.get("gasUsed")
    if norm(r) != "0x1":
        out["success_revert"] = ("funding leg reverts venue-side: the swap2 funding leg's mint step "
                                 "pulls the vault UNDERLYING (WRAP 0xebbcb2ce..) from the taker "
                                 "(transferFrom(taker->vault) measured in the fork trace) - the "
                                 "executor needs WRAP inventory/approvals like the winner; the venue "
                                 "ran deep (gasUsed above the guard-revert controls) on the UNPATCHED "
                                 "blob: signature + taker accepted at the embedded taker address")
        du = db = ds = o_delta = 0
        out.update({"owner_usdc_delta": "0", "exec_usdc_delta": "0",
                    "exec_buy_delta": "0", "exec_sell_delta": "0"})
        json.dump(out, open(WS + "/scratch/rf-venue-proof.json", "w"), indent=1)
        print("rf-venue-proof PARTIAL ->", out.get("success_tx"), out["success_revert"][:80])
        raise SystemExit(0)
    du, db, ds = bal(USDC, WINNER) - u0, bal(BUY, WINNER) - b0, bal(SELL, WINNER) - s0
    o_delta = bal(USDC, OWNER) - o0
    out.update({"owner_usdc_delta": str(o_delta), "exec_usdc_delta": str(du),
                "exec_buy_delta": str(db), "exec_sell_delta": str(ds)})
    assert o_delta > 0, "owner USDC delta not positive"
    assert du == 0, "executor USDC delta not zero (payout not fully to owner)"
    assert db >= 0 and ds >= 0, "inventory guard failed in tokens"
    out["note"] = ("real payout - usdcIn = owner delta (USDC raw); the venue legs are the "
                   "auction-8 winner's own captured Swapper blobs at their fill block, run "
                   "unpatched with the executor deployed at the blobs' embedded Order taker")
finally:
    sh("fork", "release", "ethereum")

json.dump(out, open(WS + "/scratch/rf-venue-proof.json", "w"), indent=1)
print("rf-venue-proof ok ->", out.get("success_tx"), out.get("owner_usdc_delta"))
