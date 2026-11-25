"""Fork proof (base): a stranger takes the Superfluid TOGA PIC seat for USDCx with a bond, and gets the whole bond back
in the tx in which a second stranger outbids it. No executor here: this proves the mechanism for a human proposal only.
Run: python3 scratch/sf_fork_proof.py   (leases, resets to head, releases)"""
import json, subprocess, sys

CH = "base"
TOGA = "0xA87F76e99f6C8Ff8996d14f550ceF47f193D9A09"
USDCX = "0xD04383398dD2426297da660F9CCA3d439AF9ce1b"
USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
HOLDER = "0xBBBBBbbBBb9cC5e90e3b3Af64bdAF62C37EEFFCb"  # Morpho Blue on base, holds USDC
S1 = "0x00000000000000000000000000000000000FA501"
S2 = "0x00000000000000000000000000000000000Fa502"


def sh(*a):
    r = subprocess.run(list(a), capture_output=True, text=True)
    return (r.stdout + r.stderr).strip()


def cd(sig, *a):
    return sh("/opt/foundry/bin/cast", "calldata", sig, *[str(x) for x in a])


def send(frm, to, data):
    out = sh("fork", "send", CH, json.dumps({"from": frm, "to": to, "data": data}))
    print("  send", frm[-4:], "->", to[:8], data[:10], "=>", out[:300].replace("\n", " "))
    return out


def call(to, data):
    out = sh("fork", "call", CH, json.dumps({"to": to, "data": data}))
    return out


def bal(tok, who):
    o = call(tok, cd("balanceOf(address)", who))
    try:
        h = o.split("0x")[-1].split('"')[0].strip()
        return int(h, 16)
    except Exception:
        return o


def pic():
    o = call(TOGA, cd("getCurrentPICInfo(address)", USDCX))
    h = o.split("0x")[-1].split('"')[0].strip()
    return "0x" + h[24:64], int(h[64:128], 16) / 1e18, int(h[128:192], 16)


print(sh("fork", "lease", CH, "10", "superfluid toga proof 56e8c1ce"))
try:
    print(sh("fork", "reset", CH))
    print("block", sh("/opt/foundry/bin/cast", "block-number", "--rpc-url", sh("fork", "url", CH)))
    p0 = pic()
    print("PIC before:", p0)
    old = p0[0]
    old_bal0 = bal(USDCX, old)
    for s in (S1, S2):
        print(sh("fork", "fund", CH, s, "1"))
        print(sh("fork", "fund-token", CH, USDC, HOLDER, s, str(400 * 10**6))[:200])
        send(s, USDC, cd("approve(address,uint256)", USDCX, 400 * 10**6))
        send(s, USDCX, cd("upgrade(uint256)", 400 * 10**18))
        send(s, USDCX, cd("approve(address,uint256)", TOGA, 400 * 10**18))
    b1 = int((p0[1] + 5) * 1e18)
    print("S1 USDCx before bond:", bal(USDCX, S1) / 1e18)
    print("GUARD: bid below the current bond must revert")
    send(S1, USDCX, cd("send(address,uint256,bytes)", TOGA, int(p0[1] * 0.5 * 1e18), "0x"))
    print("PIC after low bid:", pic())
    print("SUCCESS: bid above the current bond")
    send(S1, USDCX, cd("send(address,uint256,bytes)", TOGA, b1, "0x"))
    p1 = pic()
    print("PIC after S1 bond:", p1, "is S1:", p1[0].lower() == S1.lower())
    print("old PIC USDCx gain: %.6f" % ((bal(USDCX, old) - old_bal0) / 1e18))
    print("S1 USDCx after bond: %.6f" % (bal(USDCX, S1) / 1e18))
    print("S2 outbids")
    b2 = int((p1[1] + 5) * 1e18)
    send(S2, USDCX, cd("send(address,uint256,bytes)", TOGA, b2, "0x"))
    p2 = pic()
    print("PIC after S2 bond:", p2, "is S2:", p2[0].lower() == S2.lower())
    print("S1 USDCx after being outbid: %.6f (started 400)" % (bal(USDCX, S1) / 1e18))
    send(S1, USDCX, cd("downgrade(uint256)", bal(USDCX, S1)))
    print("S1 USDC after downgrade: %.6f (started 400)" % (bal(USDC, S1) / 1e6))
finally:
    print(sh("fork", "release", CH))
