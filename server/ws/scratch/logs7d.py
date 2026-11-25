import subprocess, json, collections
RPC=['python3','/srv/farm/ws/tools/rpc.py','ethereum']
def rpc(m,p,tries=2):
    for i in range(tries+1):
        r=subprocess.run(RPC+[m,json.dumps(p)],capture_output=True,text=True)
        try: d=json.loads(r.stdout)
        except Exception as e: continue
        if 'result' in d: return d['result']
        print('ERR',json.dumps(d)[:200])
    raise SystemExit('fail '+m)
vaults=["0x0a2b94f6871c1d7a32fe58e1ab5e6dea2f114e56","0x6dc3ce9c57b20131347fdc9089d740daf6eb34c5","0xe800e3760fc20aa98c5df6a9816147f190455af3","0x35911af1b570e26f668905595ded133d01cd3e5a","0xa7569a44f348d3d70d8ad5889e50f78e33d80d35","0x79eb84b5e30ef2481c8f00fd0aa7aad6ac0aa54d","0x408b6a3e2daf288864968454aae786a2a042df36","0x52f0d57fb5d4780a37164f918746f9bd51c684a3","0xc7d7f434c015f2a7e77df9763ade300f2171a05a","0x1abd0403591be494771115d74ed9e120530f356e","0x2916dfb3324377645cac4c5e78dffce910a61393","0xd6246604313bd2884d205285aeefae07068fc58e"]
FR,TO=26416160,26466416
logs=rpc('eth_getLogs',[{'fromBlock':hex(FR),'toBlock':hex(TO),'address':vaults}])
print("total logs in 7d (blocks",FR,"-",TO,"):",len(logs))
c=collections.Counter(l['topics'][0] for l in logs)
for t,n in c.most_common(12): print(t[:20],n)
import collections as cc
txs=cc.Counter(l['transactionHash'] for l in logs)
print("distinct txs:",len(txs))
json.dump(logs,open('scratch/logs7d.json','w'))
