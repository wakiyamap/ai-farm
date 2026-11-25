"""Measure what a Uniswap V2 skim(address) call pays, from the token transfers in its trace."""
import json, subprocess, sys

WS = "/srv/farm/ws"

def rpc(chain, method, params):
    p = subprocess.run(["python3", f"{WS}/tools/rpc.py", chain, method, json.dumps(params)],
                       capture_output=True, text=True)
    if p.returncode != 0:
        return {"_err": (p.stdout + p.stderr)[:300]}
    try:
        return json.loads(p.stdout).get("result")
    except Exception:
        return {"_err": p.stdout[:200]}

HASHES = [
    "0x2d8fccb36bd82df329fd04d9fa49f9cfc37c99cdfd25bb339c9b8f7d33b09581",
    "0x940886c089f8b19d4d680e2ed7b0b49b24cd413e5b9679cb8b3176612639ad48",
    "0xf6ec44dcba9eeeb12f42c8635161769fccb5edd6c1ec9146dbd4898b54f60471",
    "0xb9ff5871c15230040ad4bec93ffaf8606e9dc102bd1b5b9c791d6a94064ac273",
    "0xe7b73e4089d1857a988b2c40ee491d2fd9194f74db4bfd95e56097a942717a50",
]
DEC = {"0x4200000000000000000000000000000000000006": 18, "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913": 6}

for h in HASHES:
    tr = rpc("base", "debug_traceTransaction", [h, {"tracer": "callTracer"}])
    rc = rpc("base", "eth_getTransactionReceipt", [h])
    if not isinstance(tr, dict) or "_err" in tr:
        print(h, "trace err", tr); continue
    r = tr
    calls = r.get("calls", []) or []
    xfer = []
    for c in calls:
        inp = c.get("input", "")
        if inp.startswith("0xa9059cbb") and len(inp) >= 138:
            tok = c.get("to", "").lower()
            recip = "0x" + inp[34:74]
            amt = int(inp[74:138], 16)
            d = DEC.get(tok)
            xfer.append((tok[:10], recip[:10], amt, d))
    gas_used = int(rc["result"]["gasUsed"], 16) if isinstance(rc, dict) and "result" in rc else None
    gp = int(rc["result"]["effectiveGasPrice"], 16) if isinstance(rc, dict) and "result" in rc else None
    print(f"{h[:16]} from={r.get('from','')[:12]} gasUsed={gas_used} gasPrice_gwei={None if gp is None else round(gp/1e9,5)}")
    for tok, recip, amt, d in xfer:
        print(f"    -> {recip} {amt} raw ({'18' if d==18 else '6' if d==6 else '?'} dec) tok={tok}")
    if not xfer:
        print("    no token transfers (inputs:", [c.get("input","")[:10] for c in calls], ")")
