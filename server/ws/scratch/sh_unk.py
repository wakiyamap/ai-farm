import subprocess, json
POOL = "0x528d46B5780879E28Cf410C0b86D991A38Fe64Aa"
FRESH = "0x000000000000000000000000000000000000dEaD".lower()
def rpc(method, params, lane="paper"):
    p = subprocess.run(["python3", "/srv/farm/ws/tools/rpc.py", "bsc", method,
                        json.dumps(params, separators=(",", ":")), "--lane", lane],
                       capture_output=True, text=True)
    try:
        r = json.loads(p.stdout)
        return r.get("result", r.get("error", {}).get("message", ""))
    except Exception:
        return (p.stdout or p.stderr)[:150]

pad = lambda x: x[2:].lower().rjust(64, "0")
for s in ["0a12f521", "1afcd79f", "2a875269", "334bd919", "703e46dd", "7965db0b", "f0330054"]:
    d1 = "0x" + s + pad(FRESH)
    d2 = "0x" + s + pad(FRESH) + (1).to_bytes(32, "big").hex()
    r1 = rpc("eth_call", [{"to": POOL, "data": d1, "from": "0x1111111111111111111111111111111111111111"}, "latest"])
    r2 = rpc("eth_call", [{"to": POOL, "data": d2, "from": "0x1111111111111111111111111111111111111111"}, "latest"])
    print(s, "| +addr:", str(r1)[:100], "| +addr,uint:", str(r2)[:100])
