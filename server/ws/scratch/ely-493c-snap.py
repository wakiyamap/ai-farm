"""Instant USDC/WHYPE mid-price snapshot across Elysium v3-style and Aero CL pools (lead 200 pre-check)."""
import json, subprocess

RPC = "/srv/farm/ws/tools/rpc.py"
USDC = "0xb47c4C8F73F009CC0C0d3f92B388d13E293F0B65"
WHYPE = "0xba876237b0f021a6c6d852d6c26e107997cc5e81"
V3F = "0x1707327F626496A7b5b3872e7E4d2879Df7d7a9f"
AEROF = "0xEfd7A089D3057F05189B05f74Ffcf30610c42891"
KNOWN = ["0x97796d80b6a1db78632f7451196b04f307329eb6", "0xd329b88ba62483918c3f6c9421178345cf9eebc2"]
ZERO = "0x" + "0" * 40


def cast(*a):
    return subprocess.run(["/opt/foundry/bin/cast", *a], capture_output=True, text=True).stdout.strip()


def call(to, data):
    o = subprocess.run(["python3", RPC, "elysium", "eth_call", json.dumps([{"to": to, "data": data}, "latest"]), "--lane", "research"],
                       capture_output=True, text=True).stdout
    j = json.loads(o)
    return j.get("result")


pools = {}
for fee in (100, 500, 3000, 10000):
    r = call(V3F, cast("calldata", "getPool(address,address,uint24)", USDC, WHYPE, str(fee)))
    if r and int(r, 16):
        pools["v3 fee%d" % fee] = "0x" + r[-40:]
for ts in (1, 10, 50, 100, 200, 2000):
    r = call(AEROF, cast("calldata", "getPool(address,address,int24)", USDC, WHYPE, str(ts)))
    if r and int(r, 16):
        pools["aero ts%d" % ts] = "0x" + r[-40:]
for k in KNOWN:
    if k not in [p.lower() for p in pools.values()]:
        pools["lead184 " + k[:8]] = k

S0 = cast("sig", "slot0()")
LIQ = cast("sig", "liquidity()")
T0 = cast("sig", "token0()")
FEE = cast("sig", "fee()")
usdc_sel = cast("calldata", "balanceOf(address)", "0x" + "0" * 40)[:10]
for name, p in pools.items():
    s = call(p, S0)
    t0 = call(p, T0)
    fee = call(p, FEE)
    bal = call(USDC, cast("calldata", "balanceOf(address)", p))
    if not s:
        print(name, p, "slot0 failed")
        continue
    sp = int(s[2:66], 16)
    price = (sp / 2 ** 96) ** 2  # token1 per token0 in raw units
    t0a = "0x" + t0[-40:] if t0 else "?"
    if t0a.lower() == USDC.lower():
        whype_per_usdc = price * 1e6 / 1e18
        usdc_per_whype = 1 / whype_per_usdc if whype_per_usdc else 0
    else:
        usdc_per_whype = price * 1e18 / 1e6
    print(f"{name:18s} {p} fee={int(fee,16) if fee else '?'} usdc_bal={int(bal,16)/1e6 if bal else '?':.0f} USDC/WHYPE={usdc_per_whype:.4f}")
