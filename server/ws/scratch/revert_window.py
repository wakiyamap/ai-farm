import datetime
import json
import subprocess

head = json.load(open('scratch/revert-head.json'))['result']
hi = int(head['number'], 16)
ts = int(head['timestamp'], 16)
target = ts - 7 * 86400

def block(n):
    s = subprocess.check_output(['python3','tools/rpc.py','ethereum','eth_getBlockByNumber',json.dumps([hex(n),False])], text=True)
    b = json.loads(s)['result']
    return int(b['timestamp'],16)

lo = hi - 100000
while hi - lo > 1:
    mid = (lo + hi)//2
    if block(mid) < target:
        lo = mid
    else:
        hi = mid
print(json.dumps({'from_block':hi,'from_time':datetime.datetime.fromtimestamp(block(hi),datetime.timezone.utc).isoformat(),'to_block':int(head['number'],16),'to_time':datetime.datetime.fromtimestamp(ts,datetime.timezone.utc).isoformat(),'target_time':datetime.datetime.fromtimestamp(target,datetime.timezone.utc).isoformat()}))
