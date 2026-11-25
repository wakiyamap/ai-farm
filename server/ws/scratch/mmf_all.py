import subprocess, json
from collections import Counter
def rpc(m,p): return json.loads(subprocess.run(['python3','/srv/farm/ws/tools/rpc.py','optimism',m,json.dumps(p)],capture_output=True,text=True).stdout)['result']
logs=json.load(open('scratch/mmf_logs2.json'))
txs=list(dict.fromkeys(l['transactionHash'] for l in logs))
sel=Counter(); frm=Counter()
for h in txs:
    out=rpc('eth_getTransactionByHash',[h])
    if not out: continue
    sel[out['input'][:10]]+=1; frm[out['from'].lower()]+=1
print('selectors over all 73 mmf txs:', dict(sel))
print('distinct callers:', len(frm))
for a,n in frm.most_common(10): print(a,n)
json.dump({'sel':dict(sel),'frm':dict(frm)}, open('scratch/mmf_all.json','w'))
