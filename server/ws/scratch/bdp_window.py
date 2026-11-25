import datetime as dt
import json
import subprocess

def rpc(method, params):
    p = subprocess.run(['python3','/srv/farm/ws/tools/rpc.py','ethereum',method,json.dumps(params)],capture_output=True,text=True)
    if p.returncode: raise RuntimeError(p.stdout+' '+p.stderr)
    d = json.loads(p.stdout)
    return d['result']

head = rpc('eth_getBlockByNumber',['latest',False])
latest_num = int(head['number'],16)
target = int(dt.datetime.now(dt.timezone.utc).timestamp()) - 7*86400
lo,hi = latest_num-100000,latest_num
while lo < hi:
    mid=(lo+hi)//2
    block=rpc('eth_getBlockByNumber',[hex(mid),False])
    if int(block['timestamp'],16)<target: lo=mid+1
    else: hi=mid
start=rpc('eth_getBlockByNumber',[hex(lo),False])
print(json.dumps({'start':{'number':lo,'timestamp':int(start['timestamp'],16),'utc':dt.datetime.fromtimestamp(int(start['timestamp'],16),dt.timezone.utc).isoformat()},'head':{'number':latest_num,'timestamp':int(head['timestamp'],16),'utc':dt.datetime.fromtimestamp(int(head['timestamp'],16),dt.timezone.utc).isoformat()}}))
