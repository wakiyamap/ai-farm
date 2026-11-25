import json, subprocess, sys
def rpc(method, params):
    out = subprocess.run(["python3","tools/rpc.py","bsc",method,json.dumps(params)],capture_output=True,text=True)
    try:
        d = json.loads(out.stdout)
    except Exception:
        raise SystemExit(f"{method} bad json: {out.stdout[:200]} {out.stderr[:200]}")
    if "error" in d: raise SystemExit(f"{method} error: {d['error']}")
    return d["result"]
def ts(block):
    b = rpc("eth_getBlockByNumber",[hex(block) if block!="latest" else "latest", False])
    return int(b["timestamp"],16), int(b["number"],16)
