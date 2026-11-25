import subprocess, json
LATEST=60073271; FROM=56973271; step=450000
logs=[]
a=FROM
while a<=LATEST:
    b=min(a+step-1,LATEST)
    params=[{"address":"0xBBBBBbbBBb9cC5e90e3b3Af64bdAF62C37EEFFCb","fromBlock":hex(a),"toBlock":hex(b),"topics":["0xa4946ede45d0c6f06a0f5ce92c9ad3b4751452d2fe0e25010783bcab57a67e41",None,"0x0000000000000000000000001da8f0817311f4e4c8a9d3fd756c8757d566e5fd"]}]
    r=subprocess.run(['python3','tools/rpc.py','base','eth_getLogs',json.dumps(params)],capture_output=True,text=True)
    try:
        out=json.loads(r.stdout)['result']
    except Exception as e:
        print("ERR",a,r.stdout[:200],r.stderr[:200]); a=b+1; continue
    logs+=out; a=b+1
print("total liquidate logs:",len(logs))
# timestamps: need blocks -> use one getBlock per unique block? too many calls; use tx-level grouping instead
json.dump(logs,open('scratch/liq_logs.json','w'))
from collections import Counter, defaultdict
mk=Counter(l['topics'][1] for l in logs)
print("markets:", {k[:12]:v for k,v in mk.most_common(10)})
# sums
rep=sum(int(l['data'][10:74],16) for l in logs)
seiz=sum(int(l['data'][138:202],16) for l in logs)
print("repaid USDC total:",rep/1e6,"seized cbBTC total:",seiz/1e8)
# distinct txs
txs=set(l['transactionHash'] for l in logs)
print("distinct txs:",len(txs))
# per-day via block hex -> approximate by unique blocks & timestamps later
blocks=sorted(set(int(l['blockNumber'],16) for l in logs))
print("block range:",blocks[0],blocks[-1])
# group liquidations per tx
c=Counter(l['transactionHash'] for l in logs)
vals=sorted(c.values(),reverse=True)
print("liq per tx: max",vals[0],"median-ish",vals[len(vals)//2])
