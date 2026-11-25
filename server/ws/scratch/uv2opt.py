import json, subprocess, sys
CHAIN='optimism'
F='0x0c3c1c532F1e39EdF36BE9Fe0bE1410313E074Bf'
def rpc(method, params):
    out = subprocess.run(['python3','/srv/farm/ws/tools/rpc.py',CHAIN,method,json.dumps(params)],
                         capture_output=True, text=True)
    try:
        d = json.loads(out.stdout)
    except Exception:
        return {'_err': out.stdout[:200]+out.stderr[:200]}
    if 'error' in d: return {'_err': d['error'].get('message','?')}
    return d['result']
def call(to, data):
    r = rpc('eth_call',[{'to':to,'data':data},'latest'])
    return r
def sel(s):
    return subprocess.run(['cast','sig',s],capture_output=True,text=True).stdout.strip()
def callfn(to, sig, args_enc=''):
    return call(to, sel(sig)+args_enc)
def addr(w): return '0x'+w[-40:]
