import subprocess, json, sys
POOL = "0x528d46B5780879E28Cf410C0b86D991A38Fe64Aa"
USDT = "00000000000000000000000055d398326f99059ff775485246999027b3197955"
USDC = "0000000000000000000000008ac76a51cc950d9822d68b83fe1ad97b32cd580d"

def call(data, tag, frm=None):
    tx = {"to": POOL, "data": data}
    if frm:
        tx["from"] = frm
    params = json.dumps([tx, "latest"])
    p = subprocess.run(
        ["python3", "/srv/farm/ws/tools/rpc.py", "bsc", "eth_call", params, "--lane", "paper"],
        capture_output=True, text=True)
    try:
        r = json.loads(p.stdout)
        out = r.get("result") or r.get("error", {}).get("message", "")[:150]
    except Exception:
        out = (p.stdout or p.stderr)[:150]
    print(f"{tag:30s} {out[:170]}")
    return out if isinstance(out, str) else ""

call("0xa27b96be" + USDT, "poolTokenAmounts(USDT)")
call("0xa27b96be" + USDC, "poolTokenAmounts(USDC)")
call("0xa693600b", "poolAmount()")
call("0x5c975abb", "paused()")
call("0xd365a08e", "masterAddress()")
call("0xd28682ea" + USDT, "getPoolBalance(USDT)")
for s in ["0a12f521", "1afcd79f", "2a875269", "334bd919", "703e46dd", "7965db0b", "f0330054"]:
    call("0x" + s, "unk " + s)
