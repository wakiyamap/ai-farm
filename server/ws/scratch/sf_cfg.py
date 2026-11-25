import json, subprocess
HOST = "0x4C073B3baB6d8826b8C5b229f3cfdC1eC6E47E74"
TOGA = "0xA87F76e99f6C8Ff8996d14f550ceF47f193D9A09"
USDCX = "0xd04383398dd2426297da660f9cca3d439af9ce1b"
def cd(sig, *a):
    return subprocess.run(["/opt/foundry/bin/cast", "calldata", sig, *a], capture_output=True, text=True).stdout.strip()
def call(to, data, frm=None):
    tx = {"to": to, "data": data}
    if frm: tx["from"] = frm
    r = subprocess.run(["python3", "/srv/farm/ws/tools/rpc.py", "base", "eth_call", json.dumps([tx, "latest"])], capture_output=True, text=True)
    return r.stdout.strip()
g = json.loads(call(HOST, cd("getGovernance()")))["result"]
gov = "0x" + g[26:]
print("governance", gov)
print("getPPPConfig(host,USDCx) [liquidationPeriod, patricianPeriod]:", call(gov, cd("getPPPConfig(address,address)", HOST, USDCX)))
print("minBondDuration:", call(TOGA, cd("minBondDuration()")))
print("getRewardAddress(host,USDCx):", call(gov, cd("getRewardAddress(address,address)", HOST, USDCX)))
print("USDCx getUnderlyingToken:", call(USDCX, cd("getUnderlyingToken()")))
# stranger open-to-anyone probe: bond() from a fresh address with no balance must fail on transferFrom, not on a role check
print("bond() from fresh addr (expect token-balance/allowance revert, no role error):", call(TOGA, cd("bond(address,uint256,int96)", USDCX, "100000000000000000000", "0"), "0x00000000000000000000000000000000000fa123")[:400])
