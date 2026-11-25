#!/usr/bin/env python3
import json, subprocess, statistics, collections
from concurrent.futures import ThreadPoolExecutor
BNB=547.0380008209854; EXE="0x0000000000be226afde21672a5e4adc45692e69d"; RYDE4="0x6a2b0b704650a93f7495d728c3b851a1c5f73172"
TP="0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
def rpc(method, params, tries=4):
    for i in range(tries):
        r=subprocess.run(["python3","/srv/farm/ws/tools/rpc.py","bsc",method,json.dumps(params)],capture_output=True,text=True)
        if r.returncode==0: return json.loads(r.stdout)["result"]
    return None
rows=json.load(open("/srv/farm/ws/scratch/s4-ryde-rows.json"))
takes={r["hash"] for r in rows}
pf=[r["prio"]/1e9 for r in rows]
print("priority fee gwei: median",round(statistics.median(pf),4),"min",round(min(pf),4),"max",round(max(pf),4),
      " p90",round(sorted(pf)[int(.9*len(pf))],4))
withg=[r for r in rows if r["gross_bnb"]]
big=sorted(withg,key=lambda r:-r["gross_bnb"])[:5]
rest=[r for r in rows if r not in big]
step=max(1,len(rest)//15)
sample=big+rest[::step][:15]
print("sample size",len(sample))
def work(r):
    rc=rpc("eth_getTransactionReceipt",[r["hash"]])
    if not rc: r["err"]="no receipt"; return r
    ti=int(rc["transactionIndex"],16); gu=int(rc["gasUsed"],16); egp=int(rc.get("effectiveGasPrice","0x0"),16)
    r.update(idx=ti, gas_used=gu, gas_usd=gu*egp/1e18*BNB, status=rc["status"], egp_gwei=egp/1e9)
    return r
with ThreadPoolExecutor(5) as ex: sample=list(ex.map(work,sample))
# trigger probe: last RYDE4 transfer before the take that is not itself a take tx
def probe(r):
    if r.get("err"): return r
    b=r["block"]
    lg=rpc("eth_getLogs",[{"address":RYDE4,"topics":[TP],"fromBlock":hex(max(0,b-15)),"toBlock":hex(b)}])
    if lg is None: r["trig"]="probe failed"; return r
    best=None
    for l in sorted(lg,key=lambda l:(int(l["blockNumber"],16),int(l["transactionIndex"],16),int(l["logIndex"],16))):
        lb=int(l["blockNumber"],16); li=int(l["transactionIndex"],16)
        if l["transactionHash"] in takes: continue
        if (lb,li) < (b,r.get("idx",10**9)): best=(lb,li)
    if best is None: r["trig"]="none in 16 blocks"; r["dblocks"]=None
    else: r["trig"]="ok"; r["dblocks"]=b-best[0]; r["trig_blk"],r["trig_idx"]=best
    return r
with ThreadPoolExecutor(5) as ex: sample=list(ex.map(probe,sample))
json.dump(sample,open("/srv/farm/ws/scratch/s4-ryde-sample.json","w"))
print(f"{'block':>10} {'idx':>4} {'gross_usd':>9} {'prio_gwei':>9} {'gas_usd':>8} {'dblk':>4} taker")
for r in sorted(sample,key=lambda r:-(r["gross_bnb"] or 0)):
    print(f"{r['block']:>10} {str(r.get('idx')):>4} {round((r['gross_bnb'] or 0)*BNB,3):>9} {round(r['prio']/1e9,4):>9} {round(r.get('gas_usd',0),4):>8} {str(r.get('dblocks')):>4} {r['frm'][:14]}")
ok=[r for r in sample if r.get("dblocks") is not None]
print("dblocks: median",statistics.median([r["dblocks"] for r in ok]),"max",max([r["dblocks"] for r in ok]),"n",len(ok))
g=[r["gross_bnb"] for r in sample if r["gross_bnb"]]
print("SAMPLE medians: gross USD",round(statistics.median(g)*BNB,3),"gas USD",round(statistics.median([r["gas_usd"] for r in sample if "gas_usd" in r]),4),
      "prio gwei",round(statistics.median([r["prio"]/1e9 for r in sample]),4))
print("tx index distribution (sample):",sorted(r.get("idx",-1) for r in sample))
