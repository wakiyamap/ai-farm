import datetime
import json
import subprocess

target = int(datetime.datetime(2026, 11, 16, 20, 36, tzinfo=datetime.timezone.utc).timestamp())
def block(n):
    p = subprocess.run(['python3','/srv/farm/ws/tools/rpc.py','ethereum','eth_getBlockByNumber',json.dumps([hex(n),False])],capture_output=True,text=True,check=True)
    x = json.loads(p.stdout)['result']
    return int(x['number'],16), int(x['timestamp'],16)
head = block(26480266)
lo,hi = head[0]-60000,head[0]
while lo < hi:
    mid=(lo+hi)//2
    if block(mid)[1] < target: lo=mid+1
    else: hi=mid
print('start',block(lo),'head',head,'target',target)
