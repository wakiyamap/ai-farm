import json
import os
import urllib.request
from pathlib import Path

out = Path('/srv/farm/ws/scratch/euler_avax_audit')
url = os.environ['RPC_RELAY_URL'].rstrip('/') + '/avalanche'
factory = '0xaf4B4c18B17F6a2B32F6c398a3910bdCD7f26181'

def rpc(method, params):
    body=json.dumps({'jsonrpc':'2.0','id':1,'method':method,'params':params}).encode()
    with urllib.request.urlopen(urllib.request.Request(url,body,{'Content-Type':'application/json'}),timeout=60) as r:
        result=json.load(r)
    if 'error' in result: raise RuntimeError(result['error'])
    return result['result']

def get_block(n):
    return rpc('eth_getBlockByNumber',[hex(n),False])

head=int(rpc('eth_blockNumber',[]),16)
head_ts=int(get_block(head)['timestamp'],16)
lo=max(0,head-400000)
hi=head
target=head_ts-7*86400
while hi-lo>1:
    mid=(lo+hi)//2
    if int(get_block(mid)['timestamp'],16)<target: lo=mid
    else: hi=mid
start=lo
length=int(rpc('eth_call',[{'to':factory,'data':'0x0a68b7ba'},'latest']),16)
addresses=[]
for i in range(length):
    result=rpc('eth_call',[{'to':factory,'data':'0x378cdb62'+f'{i:064x}'},'latest'])
    addresses.append('0x'+result[-40:])
    if i and i%50==0: print('addresses',i,flush=True)
(out/'all_vaults.json').write_text(json.dumps({'head':head,'head_ts':head_ts,'start':start,'start_ts':int(get_block(start)['timestamp'],16),'target_ts':target,'length':length,'addresses':addresses},indent=2))
topics={}
errors=[]
total=0
for page_start in range(start,head+1,10000):
    page_end=min(head,page_start+9999)
    for batch_start in range(0,length,32):
        batch=addresses[batch_start:batch_start+32]
        try:
            logs=rpc('eth_getLogs',[{'fromBlock':hex(page_start),'toBlock':hex(page_end),'address':batch}])
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
    (out/'full_scan.json').write_text(json.dumps({'head':head,'start':start,'head_ts':head_ts,'start_ts':int(get_block(start)['timestamp'],16),'addresses':length,'logs':total,'topics':topics,'errors':errors,'last_page':page_end},indent=2))
