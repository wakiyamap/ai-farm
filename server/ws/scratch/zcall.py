import json, subprocess
def sel(sig):
    return subprocess.run(["cast","sig",sig],capture_output=True,text=True).stdout.strip()
def call(to, data, frm=None):
    tx={"to":to,"data":data}
    if frm: tx["from"]=frm
    r=subprocess.run(["python3","/srv/farm/ws/tools/rpc.py","base","eth_call",json.dumps([tx,"latest"])],capture_output=True,text=True)
    try:
        d=json.loads(r.stdout)
        return d.get("result", d.get("error"))
    except Exception:
        return (r.stdout+r.stderr)[:160]
def u(h):
    if not isinstance(h,str) or not h.startswith("0x") or len(h)<3: return None
    return int(h,16)
