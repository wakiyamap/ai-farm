import subprocess, json, collections
d=json.load(open('scratch/callers.json'))
RPC=['python3','/srv/farm/ws/tools/rpc.py','ethereum']
def rpc(m,p):
    for _ in range(2):
        r=subprocess.run(RPC+[m,json.dumps(p)],capture_output=True,text=True)
        if r.returncode==0:
            return json.loads(r.stdout).get('result')
    return None
agg=collections.defaultdict(lambda:[0,0])
for kind in ('ddr','rs'):
    for h in d[kind]:
        rc=rpc('eth_getTransactionReceipt',[h])
        if not rc: print('null',h); continue
        k=(kind,rc['from'].lower())
        agg[k][0]+=1; agg[k][1]+=int(rc['gasUsed'],16)
for k,v in sorted(agg.items()):
    print(k[0],k[1],'txs',v[0],'avggas',v[1]//v[0])
