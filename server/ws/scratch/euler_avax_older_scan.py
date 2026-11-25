import json
import os
import urllib.request
from pathlib import Path

out=Path('/srv/farm/ws/scratch/euler_avax_audit')
previous=json.loads((out/'full_scan.json').read_text())
vaults=json.loads((out/'all_vaults.json').read_text())['addresses']
url=os.environ['RPC_RELAY_URL'].rstrip('/')+'/avalanche'

def rpc(method,params):
    body=json.dumps({'jsonrpc':'2.0','id':1,'method':method,'params':params}).encode()
    with urllib.request.urlopen(urllib.request.Request(url,body,{'Content-Type':'application/json'}),timeout=60) as r:
        obj=json.load(r)
    if 'error' in obj: raise RuntimeError(obj['error'])
    return obj['result']

def ts(n): return int(rpc('eth_getBlockByNumber',[hex(n),False])['timestamp'],16)

head=previous['head']
target=previous['head_ts']-7*86400
lo=head-1000000
hi=previous['start']
assert ts(lo)<target<=ts(hi)
while hi-lo>1:
    mid=(lo+hi)//2
    if ts(mid)<target: lo=mid
    else: hi=mid
start=lo
end=previous['start']-1
topics={}
errors=[]
total=0
for page_start in range(start,end+1,10000):
    page_end=min(end,page_start+9999)
    for batch_start in range(0,len(vaults),32):
        try:
            logs=rpc('eth_getLogs',[{'fromBlock':hex(page_start),'toBlock':hex(page_end),'address':vaults[batch_start:batch_start+32]}])
            total+=len(logs)
            for log in logs:
                key=log['topics'][0] if log['topics'] else '(none)'
                entry=topics.setdefault(key,{'count':0,'example':log,'first':int(log['blockNumber'],16),'last':int(log['blockNumber'],16)})
                block=int(log['blockNumber'],16)
                entry['count']+=1
                entry['first']=min(entry['first'],block)
                entry['last']=max(entry['last'],block)
        except Exception as exc:
            errors.append({'lo':page_start,'hi':page_end,'batch_start':batch_start,'error':str(exc)})
    print('page',page_start,page_end,'logs',total,'topics',len(topics),'errors',len(errors),flush=True)
    (out/'older_scan.json').write_text(json.dumps({'head':head,'start':start,'end':end,'start_ts':ts(start),'target_ts':target,'addresses':len(vaults),'logs':total,'topics':topics,'errors':errors,'last_page':page_end},indent=2))
