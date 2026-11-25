"""Current skim-able excess (balanceOf(pair) - reserve) on the top Base Uniswap V2 pairs."""
import json, subprocess

WS = "/srv/farm/ws"
FACTORY = "0x8909dc15e40173ff4699343b6eb8132c65e18ec6"

POOLS = [
    ("OPAL-WETH", 2435490, ["0x119b63b1605be3a8ff4543c7f76f7f1f79eecd1f", "0x4200000000000000000000000000000000000006"]),
    ("WETH-DINO", 2005960, ["0x4200000000000000000000000000000000000006", "0x85e90a5430af45776548adb82ee4cd9e33b08077"]),
    ("USDC-B18", 1257557, ["0x833589fcd6edb6e08f4c7c32d4f71b54bda02913", "0xa0c8b0c06ff087d168b79177bab402f8844825cb"]),
    ("AGNT-USDC", 998764, ["0x7484a9fb40b16c4dfe9195da399e808aa45e9bb9", "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913"]),
    ("WETH-USDC", 989423, ["0x4200000000000000000000000000000000000006", "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913"]),
    ("ZUZALU-WETH", 701567, ["0x3054e8f8fba3055a42e5f5228a2a4e2ab1326933", "0x4200000000000000000000000000000000000006"]),
    ("WETH-SLOP", 695101, ["0x4200000000000000000000000000000000000006", "0xa5a3a7a1dec1a57e41a0cdd8c2129cfd7b46b592"]),
    ("CHARRED-USDC", 602747, ["0x11ff37785b849f38117a7ab2dff766c056d8ba6d", "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913"]),
    ("R1-USDC", 589385, ["0x6444c6c2d527d85ea97032da9a7504d6d1448ecf", "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913"]),
    ("WETH-KEYCAT", 563064, ["0x4200000000000000000000000000000000000006", "0x9a26f5433671751c3276a065f57e5a02d2817973"]),
]

def rpc(method, params):
    p = subprocess.run(["python3", f"{WS}/tools/rpc.py", "base", method, json.dumps(params)],
                       capture_output=True, text=True)
    if p.returncode != 0:
        return None
    try:
        return json.loads(p.stdout)["result"]
    except Exception:
        return None

def call(to, data):
    r = rpc("eth_call", [{"to": to, "data": data}, "latest"])
    return r

SEL_GETPAIR = "0xe6a43905"
SEL_TOKEN0 = "0x0dfe1681"
SEL_TOKEN1 = "0xd21220a7"
SEL_RES = "0x0902f1ac"
SEL_BAL = "0x70a08231"

def pad(a):
    return "0" * 24 + a.lower().replace("0x", "")

print(f"{'pool':16s} {'pair':44s} {'excess0 USD':>12s} {'excess1 USD':>12s}")
tot = 0.0
for sym, tvl, toks in POOLS:
    d = SEL_GETPAIR + pad(toks[0]) + pad(toks[1])
    r = call(FACTORY, d)
    if not r or int(r, 16) == 0:
        print(f"{sym:16s} no pair"); continue
    pair = "0x" + r[-40:]
    t0 = call(pair, SEL_TOKEN0); t1 = call(pair, SEL_TOKEN1)
    res = call(pair, SEL_RES)
    if not t0 or not t1 or not res or len(res) < 200:
        print(f"{sym:16s} {pair} bad data"); continue
    a0 = t0[-40:]; a1 = t1[-40:]
    r0 = int(res[26:90], 16); r1 = int(res[90:154], 16)
    b0 = int(call("0x" + a0, SEL_BAL + pad(pair))[2:], 16)
    b1 = int(call("0x" + a1, SEL_BAL + pad(pair))[2:], 16)
    e0 = b0 - r0; e1 = b1 - r1
    # price each token from the pair's own 50/50 valuation: half TVL per side
    p0 = (tvl / 2) / r0 if r0 else 0
    p1 = (tvl / 2) / r1 if r1 else 0
    v0 = e0 * p0; v1 = e1 * p1
    tot += v0 + v1
    print(f"{sym:16s} {pair:44s} {v0:12.4f} {v1:12.4f}   (raw e0={e0} e1={e1})")
print(f"total skim-able excess across these 10 pools: ${tot:.2f}")
