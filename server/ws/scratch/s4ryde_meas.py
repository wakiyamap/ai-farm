#!/usr/bin/env python3
import json, subprocess, collections
from concurrent.futures import ThreadPoolExecutor
chain="bsc"; BNB=547.0380008209854; RATE=2.218; HEAD=134978392; HTS=1795305167
EXE="0x0000000000be226afde21672a5e4adc45692e69d"
def rpc(method, params, tries=4):
    err=""
    for i in range(tries):
        r=subprocess.run(["python3","/srv/farm/ws/tools/rpc.py",chain,method,json.dumps(params)],capture_output=True,text=True)
        if r.returncode==0: return json.loads(r.stdout)["result"]
        err=(r.stderr.strip()+" | "+r.stdout.strip())[:250]
    return None
def est_ts(b): return HTS-(HEAD-b)/RATE
logs=json.load(open("/srv/farm/ws/scratch/s4-ryde4-logs.json"))
takes=sorted({(int(l["blockNumber"],16), l["transactionHash"]) for l in logs})
wd=json.load(open("/srv/farm/ws/scratch/r08a8/wd.json"))
lastwd={}
for r in wd:
    if r["exe"]==EXE: lastwd[r["hash"]]=r["bnb"]   # last Withdrawal log per tx
def fetch(h):
    t=rpc("eth_getTransactionByHash",[h]); return (h,t)
txmap={}
with ThreadPoolExecutor(6) as ex:
    for h,t in ex.map(fetch,[t[1] for t in takes]):
        txmap[h]=t
rows=[]
missing=0
for b,h in takes:
    t=txmap.get(h)
    if not t: missing+=1; continue
    g=lastwd.get(h)
    rows.append(dict(block=b,hash=h,ts=round(est_ts(b)),frm=t["from"],
        prio=int(t.get("maxPriorityFeePerGas") or t.get("gasPrice"),16),
        gwei=round(int(t.get("gasPrice","0x0"),16)/1e9,4), gross_bnb=g))
json.dump(rows,open("/srv/farm/ws/scratch/s4-ryde-rows.json","w"))
senders=collections.Counter(r["frm"] for r in rows)
print("occurrences(txs):",len(takes),"fetched:",len(rows),"missing:",missing)
print("distinct takers:",len(senders))
print("top takers:",senders.most_common(8))
gs=[r["gross_bnb"] for r in rows if r["gross_bnb"]]
gs.sort()
import statistics
print("with gross data:",len(gs),"median BNB",round(statistics.median(gs),6),"= USD",round(statistics.median(gs)*BNB,2),
      " sum BNB",round(sum(gs),4),"= USD",round(sum(gs)*BNB,0))
print("max",round(max(gs),6),round(max(gs)*BNB,2),"min",round(min(gs),8))
print("gross>0 count:",len([x for x in gs if x>0]))
# per-UTC-day histogram
days=collections.Counter()
for r in rows:
    days[__import__("datetime").datetime.utcfromtimestamp(r["ts"]).strftime("%m-%d")]+=1
print("per day:",sorted(days.items()))
print("last 5 takes:",[(r["block"],r["frm"][:12],round(r["ts"])) for r in rows[-5:]])
