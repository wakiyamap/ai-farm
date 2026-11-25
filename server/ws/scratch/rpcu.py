import json, subprocess
def rpc(m,p,chain='arbitrum'):
    r=subprocess.run(['python3','/srv/farm/ws/tools/rpc.py',chain,m,json.dumps(p)],capture_output=True,text=True)
    d=json.loads(r.stdout)
    if 'error' in d: raise ValueError(f'rpc error {m}: {d["error"]}')
    return d['result']
