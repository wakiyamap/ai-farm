import json, subprocess, sys

def rpc(method, params):
    out = subprocess.run(['python3','/srv/farm/ws/tools/rpc.py','optimism',method,json.dumps(params)],capture_output=True,text=True)
    if out.returncode != 0:
        print('RPC ERR', method, out.stderr[:200]); return None
    d = json.loads(out.stdout)
    return d.get('result', d)

def sel(sig):
    return '0x'+subprocess.run(['cast','sig',sig],capture_output=True,text=True).stdout.strip()[2:10]

def call(to, sig, args_hex=''):
    data = sel(sig)+args_hex
    r = rpc('eth_call', [{'to': to, 'data': data}, 'latest'])
    return r

def addr(hexres, i=0):
    return '0x'+hexres[2+64*i:66+64*i]
