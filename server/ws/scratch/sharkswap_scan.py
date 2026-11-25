import subprocess, json, sys
def rpc(method, params):
    r=subprocess.run(['python3','/srv/farm/ws/tools/rpc.py','base',method,json.dumps(params)],capture_output=True,text=True)
    try: d=json.loads(r.stdout)
    except: return {'_err': r.stdout[:200]+r.stderr[:200]}
    if 'error' in d: return {'_err': d['error'].get('message','')[:120]}
    return d['result']
F='0x57592D44eb60011500961EF177BFf8D8691D5a8B'
UNIV2='0x8909dc15e40173ff4699343b6eb8132c65e18ec6'
PC='0x0d3648bd0f6ba80134a33ba9275ac585d9d315f0ad8355cddefde31afa28d0e9'
SWAP='0xd78ad95fa46c994b6551d0da85fc275fe613ce37657fb8d5e3d130840159d822'
pairs=json.load(open('/tmp/ss/pairs.json'))
latest=int(rpc('eth_blockNumber',[]),16)
start=latest-3024000   # 7d at 0.2s blocks
print('latest',latest,'start',start)
out={'latest':latest,'start':start}
# 1) factory PairCreated over 7d, page 49000
def scan(addrs, topic, name, step=49000):
    total=0; logs=[]
    a=range(0,len(addrs),32)
    for chunk in a:
        sub=addrs[chunk:chunk+32]
        a0=start
        while a0<=latest:
            a1=min(a0+step-1, latest)
            res=rpc('eth_getLogs',[{'address':sub if len(sub)>1 else sub[0],'topics':[topic],'fromBlock':hex(a0),'toBlock':hex(a1)}])
            if isinstance(res,dict) and '_err' in res:
                print('ERR',name,hex(a0),res['_err']); break
            total+=len(res)
            logs+= res[-3:] if len(res)>3 else res
            a0=a1+1
        print(name,'chunk done, total',total, flush=True)
    return total, logs
pc, pclogs = scan([F], PC, 'PairCreated-7d')
out['paircreated_7d']=pc
sw, swlogs = scan(pairs, SWAP, 'Swap-7d')
out['swap_7d_pairs']=sw
out['swap_sample']=[{'block':l['blockNumber'],'tx':l['transactionHash']} for l in swlogs[-5:]]
# control: univ2 factory PairCreated last 200k blocks
a0=latest-200000; ctrl=0
while a0<=latest:
    a1=min(a0+49000-1,latest)
    res=rpc('eth_getLogs',[{'address':UNIV2,'topics':[PC],'fromBlock':hex(a0),'toBlock':hex(a1)}])
    if isinstance(res,dict): print('CTRL ERR',res); break
    ctrl+=len(res); a0=a1+1
out['ctrl_univ2_paircreated_200k']=ctrl
json.dump(out, open('/tmp/ss/scan7d.json','w'), indent=1)
print(json.dumps(out, indent=1)[:1500])
