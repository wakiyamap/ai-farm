import subprocess, json
POOL = "0x528d46B5780879E28Cf410C0b86D991A38Fe64Aa"
USDT = "0x55d398326f99059ff775485246999027b3197955"
USDC = "0x8ac76a51cc950d9822d68b83fe1ad97b32cd580d"
HEAD = 134190088

def rpc(method, params, lane="paper"):
    p = subprocess.run(["python3", "/srv/farm/ws/tools/rpc.py", "bsc", method,
                        json.dumps(params, separators=(",", ":")), "--lane", lane],
                       capture_output=True, text=True)
    try:
        r = json.loads(p.stdout)
        return r.get("result", r.get("error", {}).get("message", ""))
    except Exception:
        return (p.stdout or p.stderr)[:120]

# 7-day sample windows of pool logs (5000 blocks each, ~30 min)
for off in [200000, 500000, 900000, 1300000, 1550000]:
    lo = HEAD - off - 5000
    res = rpc("eth_getLogs", [{"address": POOL, "fromBlock": hex(lo), "toBlock": hex(HEAD - off)}])
    n = len(res) if isinstance(res, list) else res
    print(f"pool logs 7d window @{off}: {n}")

# shape control: address-only, no topics, on USDT, 100 blocks
res = rpc("eth_getLogs", [{"address": USDT, "fromBlock": hex(HEAD - 100), "toBlock": hex(HEAD)}])
print("shape control USDT addr-only 100 blk:", len(res) if isinstance(res, list) else res)

# actual token balances held by pool
def bal(token, holder):
    data = "0x70a08231" + holder[2:].lower().rjust(64, "0")
    r = rpc("eth_call", [{"to": token, "data": data}, "latest"])
    try:
        return int(r, 16) / 1e18
    except Exception:
        return r
print("pool USDT held:", bal(USDT, POOL))
print("pool USDC held:", bal(USDC, POOL))
print("master USDT held:", bal(USDT, "0x6a102c501a9eade49e6224cec7834c89112ccead"))
