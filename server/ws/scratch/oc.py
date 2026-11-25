import subprocess, json, functools
@functools.lru_cache(maxsize=None)
def sig(s):
    r=subprocess.run(["cast","sig",s],capture_output=True,text=True)
    return r.stdout.strip() if r.stdout.strip().startswith("0x") else "0x"+r.stdout.strip()
def raw(chain,method,params):
    r=subprocess.run(["python3","/srv/farm/ws/tools/rpc.py",chain,method,json.dumps(params)],capture_output=True,text=True)
    try:
        j=json.loads(r.stdout)
    except Exception:
        return {"_raw":r.stdout[:300]+r.stderr[:300]}
    if "error" in j: return {"_err":j["error"].get("message","")[:200]}
    return {"result":j["result"]}
def call(to,s,data=None,chain="base",frm="0x000000000000000000000000000000000000dEaD"):
    d = data if data else sig(s)
    r=raw(chain,"eth_call",[{"from":frm,"to":to,"data":d},"latest"])
    if "_err" in r or "_raw" in r: return r
    return {"sel":d,"hex":r["result"]}
def addr(h): return "0x"+h[-40:] if len(h)==66 else None
def addrs(h):
    x=h[2:]
    return ["0x"+x[i:i+40] for i in range(64,len(x),64)]
def uint(h):
    return int(h,16) if h and h!="0x" else None
