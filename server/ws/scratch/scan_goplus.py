import json,subprocess,sys,time,collections
def rpc(method,params,tries=3):
    for i in range(tries):
        p=subprocess.run(['python3','/srv/farm/ws/tools/rpc.py','bsc',method,json.dumps(params)],capture_output=True,text=True)
        try:
            d=json.loads(p.stdout)
            if 'result' in d: return d['result']
            sys.stderr.write(f"rpc err {p.stdout[:150]}\n")
        except Exception:
            sys.stderr.write(f"parse err {p.stdout[:150]} {p.stderr[:100]}\n")
        time.sleep(2)
    return None
head=int(rpc('eth_blockNumber',[]),16)
win=5000
blocks7d=int(604800/0.45)
lo=head-blocks7d
print(f"head={head} from={lo} windows={(head-lo)//win+1}",flush=True)
topic_counts=collections.Counter()
txs=set()
total=0
f=lo
while f<=head:
    t=min(f+win-1,head)
    r=rpc('eth_getLogs',[{"address":"0x25c9C4B56E820e0DEA438b145284F02D9Ca9Bd52","fromBlock":hex(f),"toBlock":hex(t)}])
    if r is None:
        print(f"FAIL range {f}-{t}",flush=True)
    else:
        for e in r:
            total+=1
            topic_counts[e['topics'][0]]+=1
            txs.add(e['transactionHash'])
    f=t+1
print("total_events",total,"unique_txs",len(txs),flush=True)
for k,v in topic_counts.most_common(20):
    print(k,v,flush=True)
json.dump({"total":total,"txs":sorted(txs),"topics":topic_counts.most_common(30)},open('/srv/farm/ws/scratch/goplus_scan7d.json','w'))
