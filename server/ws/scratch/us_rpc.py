import subprocess, json, time, sys
def rpc(method, params, tries=6):
    for t in range(tries):
        r = subprocess.run(['python3','/srv/farm/ws/tools/rpc.py','hyperevm',method,json.dumps(params),'--lane','paper'],capture_output=True,text=True)
        try:
            d = json.loads(r.stdout)
        except Exception:
            time.sleep(4); continue
        if 'result' in d: return d['result']
        time.sleep(4)
    raise RuntimeError(r.stdout[:200]+r.stderr[:200])
