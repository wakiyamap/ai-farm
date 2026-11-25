import subprocess, json
def rpc(m,p):
    r=subprocess.run(['python3','tools/rpc.py','arbitrum',m,json.dumps(p)],capture_output=True,text=True)
    d=json.loads(r.stdout)
    if 'error' in d: raise SystemExit('rpc error: '+json.dumps(d['error'])[:300])
    return d['result']
pools=[l.strip() for l in open('scratch/poollist.txt') if l.strip().startswith('0x')]
sel='0x01e1d037'  # totalAssets()
calldata=sel.join([])
calls=[[False,p,sel] for p in pools]
res=rpc('eth_call',[{'to':'0xca11bde05977b3631167028862be2a173976ca11','data':'0x0f28c97d'+eth(calls)}])
def eth(x): pass
