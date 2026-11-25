#!/usr/bin/env python3
"""Helper: eth_call via rpc.py for unitus scouting. Usage: uts_call.py <to> <sig> [args...]"""
import subprocess, sys, json, re

RPC = "/srv/farm/ws/tools/rpc.py"
CHAIN = "ethereum"

def sig4(s):
    out = subprocess.run(["cast", "sig", s], capture_output=True, text=True)
    return out.stdout.strip()

def enc_static(t, v):
    if t in ("address",):
        return v.lower().replace("0x", "").rjust(64, "0")
    return hex(int(v))[2:].rjoint if False else format(int(v), "x").rjust(64, "0")

def encode(sig, args):
    m = re.match(r"(\w+)\(([^)]*)\)", sig)
    name, types = m.group(1), [t for t in m.group(2).split(",") if t]
    sel = sig4(sig)[:10]
    data = sel
    # head/tail: only handle static types + single dynamic trailing arrays not needed here
    for t, v in zip(types, args):
        if t == "address":
            data += v.lower().replace("0x", "").rjust(64, "0")
        elif t == "uint256":
            data += format(int(v), "x").rjust(64, "0")
        elif t == "bool":
            data += format(1 if v in (True, "true", "1") else 0, "x").rjust(64, "0")
        else:
            raise SystemExit("unsupported type " + t)
    return data

def call(to, sig, args=(), frm=None, block="latest"):
    tx = {"to": to, "data": encode(sig, list(args))}
    if frm:
        tx["from"] = frm
    p = subprocess.run([sys.executable, RPC, CHAIN, "eth_call", json.dumps([tx, block])],
                       capture_output=True, text=True)
    try:
        d = json.loads(p.stdout)
    except Exception:
        return {"error": p.stdout[:200] + p.stderr[:200]}
    if "error" in d:
        return {"error": d["error"].get("message", "") + " " + str(d["error"].get("data", ""))[:60]}
    return {"result": d["result"]}

if __name__ == "__main__":
    to, s = sys.argv[1], sys.argv[2]
    args = sys.argv[3:]
    print(json.dumps(call(to, s, args)))
