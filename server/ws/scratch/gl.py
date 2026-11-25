import subprocess, json, sys
def gl(chain, addr, topic0, fb, tb):
    f = [{"address": addr, "fromBlock": hex(fb), "toBlock": hex(tb)}]
    if topic0: f[0]["topics"] = [topic0]
    r = subprocess.run(["python3","/srv/farm/ws/tools/rpc.py",chain,"eth_getLogs",json.dumps(f)],capture_output=True,text=True)
    try:
        d = json.loads(r.stdout)
        return d.get("result", "ERR:"+r.stdout[:120]+r.stderr[:120])
    except Exception:
        return "ERR:"+r.stdout[:120]+r.stderr[:200]
