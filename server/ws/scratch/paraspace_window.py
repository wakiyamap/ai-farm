import json, subprocess, datetime

def rpc(method, params):
    p=subprocess.run(['python3','/srv/farm/ws/tools/rpc.py','ethereum',method,json.dumps(params)],capture_output=True,text=True)
    if p.returncode: raise RuntimeError(p.stderr + p.stdout)
    d=json.loads(p.stdout)
    if 'error' in d: raise RuntimeError(str(d['error']))
    return d['result']

hi=int(rpc('eth_blockNumber',[]),16)
head=rpc('eth_getBlockByNumber',[hex(hi),False])
target=int(head['timestamp'],16)-7*86400
lo=hi-100000
while lo<hi:
    mid=(lo+hi)//2
    b=rpc('eth_getBlockByNumber',[hex(mid),False])
    if int(b['timestamp'],16)<target:lo=mid+1
    else:hi=mid
start=rpc('eth_getBlockByNumber',[hex(lo),False])
print(json.dumps({'start_block':lo,'start_time':datetime.datetime.fromtimestamp(int(start['timestamp'],16),datetime.timezone.utc).isoformat(),'end_block':int(head['number'],16),'end_time':datetime.datetime.fromtimestamp(int(head['timestamp'],16),datetime.timezone.utc).isoformat()}))
