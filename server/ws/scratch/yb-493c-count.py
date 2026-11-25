"""YieldBasis LEVAMM TokenExchange census, ethereum, last ~7 days (50400 blocks) and 30 days."""
import json, subprocess, collections

RPC = "/srv/farm/ws/tools/rpc.py"
HEAD = 26425999
AMMS = {
    "m7 WBTC": "0x7b9817eb5C49A99875138A5d52bF64a8B2cFFFFE",
    "m8 cbBTC": "0x49F51d7e279252F3C9a09678fdC65B4dBd5CB196",
    "m9 tBTC": "0x0e357Af536592F275C6Aa07b8AC2CA6EB3d0cF5a",
    "m10 WETH": "0x5f8D24F33Cc5a1D5D1bf012261E6A2214C92233c",
    "m6 WETH legacy": "0x35095d94E0f1F4a78386B7eB74BB64768A2341e4",
    "m5 tBTC v2": "0x61ED017468C8A3bE3Bac972b54fdae6eAfcbcd79",
    "m4 cbBTC v2": "0xDC90F6B111DF0c26e349d3cC8d3C357b191e109a",
    "m3 WBTC v2": "0x10B663da78055bDA0c7c26712CE1A0613AF0Ae66",
    "m2 tBTC legacy": "0xb0faaBE84076c6330A9642a6400e87CE4cAec9d4",
    "m1 cbBTC legacy": "0xB42e34Bf1f8627189e099ABDB069B9D73B521E4F",
    "m0 WBTC legacy": "0xa25306937dbA98378c32F167588F5Dc17A95c94b",
}


def cast(*a):
    return subprocess.run(["/opt/foundry/bin/cast", *a], capture_output=True, text=True).stdout.strip()


def call(method, params):
    o = subprocess.run(["python3", RPC, "ethereum", method, json.dumps(params), "--lane", "research"],
                       capture_output=True, text=True).stdout
    j = json.loads(o)
    if "error" in j:
        raise RuntimeError(j["error"])
    return j["result"]


T0 = cast("sig-event", "TokenExchange(address,uint256,uint256,uint256,uint256,uint256,uint256)")
print("topic0", T0)
FROM = HEAD - 216000
logs = []
b = FROM
while b <= HEAD:
    e = min(HEAD, b + 50000 - 1)
    logs += call("eth_getLogs", [{"address": list(AMMS.values()), "topics": [T0], "fromBlock": hex(b), "toBlock": hex(e)}])
    b = e + 1
json.dump(logs, open("/srv/farm/ws/scratch/yb-493c-logs.json", "w"))
inv = {v.lower(): k for k, v in AMMS.items()}
per = collections.defaultdict(list)
for l in logs:
    per[inv[l["address"].lower()]].append(l)
for name, addr in AMMS.items():
    ev = per.get(name, [])
    ev7 = [l for l in ev if int(l["blockNumber"], 16) >= HEAD - 50400]
    buyers = collections.Counter("0x" + l["topics"][1][-40:] for l in ev)
    last = max((int(l["blockNumber"], 16) for l in ev), default=None)
    # LEVAMM state: get_p and collateral amount
    try:
        p = int(call("eth_call", [{"to": addr, "data": cast("sig", "get_p()")}, "latest"]), 16) / 1e18
    except Exception as ex:
        p = None
    try:
        cd = call("eth_call", [{"to": addr, "data": cast("sig", "collateral_amount()")}, "latest"])
        coll = int(cd, 16) / 1e18
    except Exception:
        coll = None
    print(f"{name:16s} 30d={len(ev):4d} 7d={len(ev7):4d} buyers30d={len(buyers):3d} top={buyers.most_common(3)} last={last} get_p={p} collateral_LP={coll}")
