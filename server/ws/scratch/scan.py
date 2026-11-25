import subprocess, json, sys
def rpc(m,p):
    r=subprocess.run(['python3','tools/rpc.py','arbitrum',m,json.dumps(p)],capture_output=True,text=True)
    try: d=json.loads(r.stdout)
    except Exception: return {'_raw':r.stdout[:200]+r.stderr[:200]}
    return d
pools=[l.strip() for l in open('scratch/poollist.txt') if l.strip().startswith('0x')]
FAC='0xfd513630f697a9c1731f196185fb9eba6eaac20b'
groups=[pools[:26],pools[26:]+[FAC]]
A,B=524569573,526628116
CH=500000
tot=0
txs=set()
addrs={}
for gi,g in enumerate(groups):
    for a in range(A,B+1,CH):
        b=min(a+CH-1,B)
        d=rpc('eth_getLogs',[{'address':g,'fromBlock':hex(a),'toBlock':hex(b)}])
        if 'error' in d or '_raw' in d:
            print('ERR',gi,hex(a),hex(b),json.dumps(d)[:200]); continue
        logs=d.get('result') or []
        tot+=len(logs)
        for L in logs:
            txs.add(L['transactionHash']); addrs[L['address']]=addrs.get(L['address'],0)+1
        print(f'chunk {a}-{b} group{gi} logs={len(logs)}', flush=True)
print('TOTAL logs',tot,'distinct txs',len(txs))
for k,v in sorted(addrs.items(),key=lambda x:-x[1]): print('addr',k,v)
json.dump(sorted(txs), open('scratch/scan_txs.json','w'))
