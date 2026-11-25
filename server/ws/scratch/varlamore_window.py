import json, subprocess, datetime
def rpc(method, params):
    p=subprocess.run(['python3','/srv/farm/ws/tools/rpc.py','ethereum',method,json.dumps(params)],capture_output=True,text=True,check=True)
    return json.loads(p.stdout)['result']
latest=rpc('eth_getBlockByNumber',['latest',False]); target=int(latest['timestamp'],16)-7*86400
lo=0; hi=int(latest['number'],16)
while lo < hi:
    m=(lo+hi)//2
    b=rpc('eth_getBlockByNumber',[hex(m),False])
    if int(b['timestamp'],16)<target: lo=m+1
    else: hi=m
start=rpc('eth_getBlockByNumber',[hex(lo),False])
for b in [start,latest]:
    print(int(b['number'],16),datetime.datetime.fromtimestamp(int(b['timestamp'],16),datetime.timezone.utc).isoformat())
