import json,subprocess,datetime
def rpc(method,params):
 p=subprocess.run(['python3','/srv/farm/ws/tools/rpc.py','hyperevm',method,json.dumps(params)],capture_output=True,text=True)
 if p.returncode: raise RuntimeError(p.stderr+p.stdout)
 return json.loads(p.stdout)['result']
now=int(datetime.datetime.now(datetime.timezone.utc).timestamp())
target=now-7*86400
head=rpc('eth_getBlockByNumber',['latest',False]); hi=int(head['number'],16); lo=max(0,hi-800000)
while lo+1<hi:
 m=(lo+hi)//2; b=rpc('eth_getBlockByNumber',[hex(m),False])
 if int(b['timestamp'],16)<target: lo=m
 else: hi=m
start=rpc('eth_getBlockByNumber',[hex(hi),False])
print(json.dumps({'now':now,'target':target,'startBlock':hi,'startTimestamp':int(start['timestamp'],16),'headBlock':int(head['number'],16),'headTimestamp':int(head['timestamp'],16)}))
