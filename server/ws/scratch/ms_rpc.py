#!/usr/bin/env python3
"""Helper: rpc calls on ethereum via the farm relay tool."""
import json, subprocess, sys

RPC = ["python3", "/srv/farm/ws/tools/rpc.py", "ethereum"]

def rpc(method, params):
    out = subprocess.run(RPC + [method, json.dumps(params)], capture_output=True, text=True)
    if out.returncode != 0:
        raise RuntimeError(f"{method} failed: {out.stderr[:300]}")
    d = json.loads(out.stdout)
    if "error" in d:
        raise RuntimeError(f"{method} error: {json.dumps(d['error'])[:300]}")
    return d["result"]

SEL = {
    "symbol()": "95ea92d4",
    "name()": "06fdde03",
    "getBassets()": "d39c7efe",  # placeholder; verify with cast
}

def call(to, data, frm=None, block="latest"):
    tx = {"to": to, "data": data}
    if frm: tx["from"] = frm
    return rpc("eth_call", [tx, block])

def sel(sig):
    import subprocess
    out = subprocess.run(["cast", "sig", sig], capture_output=True, text=True)
    if out.returncode != 0:
        raise RuntimeError(f"cast sig failed: {out.stderr[:200]}")
    return out.stdout.strip().replace("0x", "")[:8]

if __name__ == "__main__":
    pass
