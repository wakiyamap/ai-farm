import json, subprocess, sys
def rpc(method, params):
    out = subprocess.run(['python3','/srv/farm/ws/tools/rpc.py','bsc',method,json.dumps(params)],capture_output=True,text=True)
    if out.returncode!=0:
        raise SystemExit(f'rpc fail {method}: {out.stderr[:300]}')
    return json.loads(out.stdout)['result']
factories = {
 'ssng':'0xd7e72f3615aa65b92a4dbdc211e296a35512988b',
 'twocrypto':'0x98EE851a00abeE0d95D08cF4CA2BdCE32aeaAF7F',
 'tricrypto':'0xc55837710bc500F1E3c7bb9dd1d51F7c5647E657'}
res={}
for name,f in factories.items():
    cnt=int(rpc('eth_call',[{'to':f,'data':'0x956aae3a'},'latest']),16)
    pools=[]
    for i in range(cnt):
        data='0x3a1d5d8e'+hex(i)[2:].rjust(64,'0')
        r=rpc('eth_call',[{'to':f,'data':data},'latest'])
        pools.append('0x'+r[-40:])
    res[name]=pools
    print(name,cnt,flush=True)
json.dump(res,open('/srv/farm/ws/scratch/bsc_curve_pools.json','w'))
