import subprocess, json
def rpc(method, params):
    r=subprocess.run(['python3','/srv/farm/ws/tools/rpc.py','base',method,json.dumps(params)],capture_output=True,text=True)
    try: d=json.loads(r.stdout)
    except: return {'_err': (r.stdout or '')[:150]+(r.stderr or '')[:150]}
    if 'error' in d: return {'_err': d['error'].get('message','')[:120]}
    return d['result']
SWAP='0xd78ad95fa46c994b6551d0da85fc275fe613ce37657fb8d5e3d130840159d822'
pairs=json.load(open('/tmp/ss/pairs.json'))
latest=59196730; start=56172730
total=0; lastlogs=[]; errs=0
for ci in range(0,len(pairs),10):
    sub=pairs[ci:ci+10]
    a0=start
    while a0<=latest:
        a1=min(a0+49000-1, latest)
        res=rpc('eth_getLogs',[{'address':sub,'topics':[SWAP],'fromBlock':hex(a0),'toBlock':hex(a1)}])
        if isinstance(res,dict) and '_err' in res:
            errs+=1; print('ERR',hex(a0),res['_err'],flush=True); break
        total+=len(res)
        if res: lastlogs+=res[-3:]
        a0=a1+1
    print('chunk',ci,'total so far',total,flush=True)
print('SWAP_7D_TOTAL',total,'errs',errs)
json.dump({'swap_7d':total,'errs':errs,'last':[{k:l[k] for k in ('blockNumber','transactionHash')} for l in lastlogs[-5:]]}, open('/tmp/ss/swap7d.json','w'))
