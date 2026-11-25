import subprocess, json, sys

def call(to, data):
    out = subprocess.run(["python3","/srv/farm/ws/tools/rpc.py","base","eth_call",
                          json.dumps([{"to":to,"data":data},"latest"])],
                         capture_output=True, text=True)
    try:
        d = json.loads(out.stdout)
        return d.get("result") or ("ERR:" + str(d.get("error",{}).get("message",""))[:120])
    except Exception:
        return "ERR:" + (out.stdout or out.stderr)[:120]

def s(data):
    if not data or not data.startswith("0x"): return data
    h = data[2:]
    if len(h) < 128: return data
    try:
        n = int(h[64:128],16)
        return bytes.fromhex(h[128:128+2*n]).decode(errors="replace")
    except Exception:
        return data

def u(data):
    if not data or not data.startswith("0x") or len(data) < 66: return data
    return int(data[2:66],16)

def addr(data):
    if not data or len(data) < 66: return data
    return "0x"+data[-40:]
