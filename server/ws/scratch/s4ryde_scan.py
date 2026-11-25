#!/usr/bin/env python3
# 7-day scan of RYDE4 transfers involving executor 0x..be226a on bsc (5000-block cap per getLogs)
import json, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
chain="bsc"
RYDE4="0x6a2b0b704650a93f7495d728c3b851a1c5f73172"
EXE="0x0000000000be226afde21672a5e4adc45692e69d"
TP="0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
EXT="0x"+"0"*24+EXE[2:]
def rpc(method, params, tries=4):
    err=""
    for i in range(tries):
        r=subprocess.run(["python3","/srv/farm/ws/tools/rpc.py",chain,method,json.dumps(params)],capture_output=True,text=True)
        if r.returncode==0: return json.loads(r.stdout)["result"]
        err=(r.stderr.strip()+" | "+r.stdout.strip())[:300]
    raise RuntimeError(err)
b0, hb = 133634946, 134978392
starts=list(range(b0,hb+1,4999))
def mk(which,a):
    tp = [TP, EXT] if which=="from" else [TP, None, EXT]
    f={"address":RYDE4,"topics":tp,"fromBlock":hex(a),"toBlock":hex(min(a+4998,hb))}
    return rpc("eth_getLogs",[f])
tasks=[(w,a) for w in ("from","to") for a in starts]
out={}
with ThreadPoolExecutor(6) as ex:
    futs={ex.submit(mk,w,a):(w,a) for w,a in tasks}
    for f in futs: pass
    for k,(w,a) in futs.items():
        out[(w,a)]=k.result()
logs=[]
for k,v in out.items(): logs+=v
json.dump(logs,open("/srv/farm/ws/scratch/s4-ryde4-logs.json","w"))
txs=sorted({l["transactionHash"] for l in logs})
blocks=sorted({int(l["blockNumber"],16) for l in logs})
print("pages",len(tasks),"logs",len(logs),"txs",len(txs))
print("blocks involved:",len(blocks))
if blocks:
    print("first blocks",blocks[:8]); print("last blocks",blocks[-8:])
