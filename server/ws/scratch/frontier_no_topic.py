import json, subprocess, collections
def rpc(method, params):
    p=subprocess.run(['python3','/srv/farm/ws/tools/rpc.py','ethereum',method,json.dumps(params)],capture_output=True,text=True)
    if p.returncode: raise RuntimeError(p.stderr or p.stdout)
    return json.loads(p.stdout)['result']
raw=rpc('eth_call',[{'to':'0x4dCf7407AE5C07f8681e1659f626E114A7667339','data':'0xb0772d0b'},'latest'])[2:]
n=int(raw[64:128],16); markets=['0x'+raw[128+i*64+24:128+(i+1)*64] for i in range(n)]
count=0; topics=collections.Counter(); emitters=collections.Counter(); samples=[]
for a in range(26430752,26480994+1,3000):
    z=min(a+2999,26480994)
    logs=rpc('eth_getLogs',[{'address':markets,'fromBlock':hex(a),'toBlock':hex(z)}])
    count+=len(logs)
    topics.update(x['topics'][0] for x in logs if x['topics'])
    emitters.update(x['address'] for x in logs)
    samples.extend((x['transactionHash'],x['address'],x['topics'][0] if x['topics'] else None) for x in logs[:2])
print(json.dumps({'logs':count,'topics':topics,'emitters':emitters,'samples':samples[:20]}))
speeds={m:int(rpc('eth_call',[{'to':'0x4dCf7407AE5C07f8681e1659f626E114A7667339','data':'0x1d7b33d7'+m[2:].rjust(64,'0')},'latest']),16) for m in markets}
print(json.dumps({'comp_speeds_nonzero':{k:v for k,v in speeds.items() if v},'checked':len(speeds)}))
