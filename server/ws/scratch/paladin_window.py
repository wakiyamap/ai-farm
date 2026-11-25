import json, subprocess, datetime

def rpc(method, params):
    out = subprocess.check_output(['python3','/srv/farm/ws/tools/rpc.py','ethereum',method,json.dumps(params)], text=True)
    obj = json.loads(out)
    if 'error' in obj: raise RuntimeError(obj['error'])
    return obj['result']

head = int(rpc('eth_blockNumber', []),16)
hi = head
head_block = rpc('eth_getBlockByNumber', [hex(head), False])
head_ts = int(head_block['timestamp'],16)
target = head_ts - 7*86400
lo = max(1,head-60000)
while lo < hi:
    mid = (lo+hi)//2
    ts = int(rpc('eth_getBlockByNumber',[hex(mid),False])['timestamp'],16)
    if ts < target: lo=mid+1
    else: hi=mid
first=rpc('eth_getBlockByNumber',[hex(lo),False])
print(json.dumps({'start_block':lo,'start_time':datetime.datetime.fromtimestamp(int(first['timestamp'],16),datetime.timezone.utc).isoformat(),'head_block':head,'head_time':datetime.datetime.fromtimestamp(head_ts,datetime.timezone.utc).isoformat()}))
