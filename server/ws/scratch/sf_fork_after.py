import json, subprocess
CH = "base"
TOGA = "0xA87F76e99f6C8Ff8996d14f550ceF47f193D9A09"
USDCX = "0xD04383398dD2426297da660F9CCA3d439AF9ce1b"
USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
S1 = "0x00000000000000000000000000000000000FA501"
S2 = "0x00000000000000000000000000000000000Fa502"
def sh(*a):
    r = subprocess.run(list(a), capture_output=True, text=True)
    return (r.stdout + r.stderr).strip()
def cd(sig, *a):
    return sh("/opt/foundry/bin/cast", "calldata", sig, *[str(x) for x in a])
def word(to, data):
    o = sh("fork", "call", CH, json.dumps({"to": to, "data": data}))
    return o.split("0x")[-1].split('"')[0].strip()
h = word(TOGA, cd("getCurrentPICInfo(address)", USDCX))
print("PIC", "0x" + h[24:64], "bond", int(h[64:128], 16) / 1e18, "exit/s", int(h[128:192], 16))
for n, a in (("S1", S1), ("S2", S2)):
    print(n, "USDCx", int(word(USDCX, cd("balanceOf(address)", a)), 16) / 1e18, "USDC", int(word(USDC, cd("balanceOf(address)", a)), 16) / 1e6)
