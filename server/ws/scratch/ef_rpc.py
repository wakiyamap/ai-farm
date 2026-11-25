#!/usr/bin/env python3
"""Helper: call rpc.py ethereum and print the raw result."""
import subprocess, sys, json

def rpc(method, params):
    out = subprocess.run(
        ["python3", "/srv/farm/ws/tools/rpc.py", "ethereum", method, json.dumps(params)],
        capture_output=True, text=True)
    if out.returncode != 0:
        raise RuntimeError(f"{method} failed: {out.stderr[:300]}")
    d = json.loads(out.stdout)
    if "error" in d:
        raise RuntimeError(f"{method} error: {json.dumps(d['error'])[:300]}")
    return d["result"]

if __name__ == "__main__":
    method = sys.argv[1]
    params = json.loads(sys.argv[2])
    print(json.dumps(rpc(method, params)))
