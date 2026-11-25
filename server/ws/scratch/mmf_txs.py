import subprocess, json
from collections import Counter
logs=json.load(open('scratch/mmf_logs2.json'))
txs=list(dict.fromkeys(l['transactionHash'] for l in logs))
print('distinct mmf txs:', len(txs))
sample = txs[:15] if len(txs)<=15 else txs[:8]+txs[-7:]
info=[]
for h in sample:
    out=json.loads(subprocess.run(['python3','/srv/farm/ws/tools/rpc.py','optimism','eth_getTransactionByHash',json.dumps([h])],capture_output=True,text=True).stdout)['result']
    if not out: continue
    info.append((h, out['to'].lower() if out['to'] else None, out['from'].lower(), out['input'][:10]))
sel=Counter(i[3] for i in info); frm=Counter(i[2] for i in info)
for i in info: print(i[0][:18], 'to',(i[1] or '')[:14], 'from', i[2][:14], i[3])
print('selectors:', dict(sel))
print('callers:', dict(frm))
json.dump(info, open('scratch/mmf_txs.json','w'))
