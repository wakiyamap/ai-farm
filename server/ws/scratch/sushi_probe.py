import subprocess, json, sys

def rpc(method, params):
    out = subprocess.run(["python3", "/srv/farm/ws/tools/rpc.py", "polygon", method, json.dumps(params)],
                         capture_output=True, text=True)
    if out.returncode != 0:
        return {"error": out.stderr.strip()[:200]}
    try:
        return json.loads(out.stdout).get("result", out.stdout)
    except Exception:
        return {"error": "parse: " + out.stdout[:200]}

def decode_str(hexres):
    if not hexres or hexres == "0x":
        return None
    h = hexres[2:]
    try:
        ln = int(h[:64], 16)
        s = bytes.fromhex(h[64:64 + ln * 2])
    except Exception:
        s = bytes.fromhex(h)
    return s.decode(errors="replace").strip("\x00")

F = "0x917933899c6a5F8E37F31E19f92CdBFF7e8FF0e2"
toks = {
    "USDCn": "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359",
    "USDCe": "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174",
    "WETH": "0x7ceB2337Df0Dd65B0d153856d1E647A4dE7F7A00",
    "WPOL": "0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270",
}

print("== latest PoolCreated (control range) ==")
latest = int(rpc("eth_blockNumber", [])["result"], 16) if isinstance(rpc("eth_blockNumber", []), dict) else 0

# symbols
for name, a in toks.items():
    r = rpc("eth_call", [{"to": a, "data": "0x95d89b41"}, "latest"])
    print(name, a, "->", decode_str(r.get("result")) if isinstance(r, dict) and "result" in r else r)

# getPool selector 0x1698ee82, packed (addr,addr,uint24)
def getpool(a, b, fee):
    a2, b2 = sorted([a.lower(), b.lower()])
    data = "0x1698ee82" + a2[2:].rjust(64, "0") + b2[2:].rjust(64, "0") + hex(fee)[2:].rjust(64, "0")
    r = rpc("eth_call", [{"to": F, "data": data}, "latest"])
    res = r.get("result") if isinstance(r, dict) else None
    if res and res != "0x" and int(res, 16) != 0:
        return "0x" + res[-40:]
    return None

for (n1, n2) in [("USDCe", "WETH"), ("USDCe", "WPOL"), ("WETH", "WPOL"), ("USDCn", "WETH"), ("USDCn", "WPOL")]:
    for fee in (500, 3000):
        p = getpool(toks[n1], toks[n2], fee)
        print(n1, n2, fee, "->", p)
