import json, subprocess, datetime
def rpc(method, params):
 p=subprocess.run(['python3','/srv/farm/ws/tools/rpc.py','hyperevm',method,json.dumps(params)],capture_output=True,text=True)
 if p.returncode: raise RuntimeError(p.stderr or p.stdout)
 return json.loads(p.stdout)['result']
head=int(rpc('eth_blockNumber',[]),16)
hi=rpc('eth_getBlockByNumber',[hex(head),False]); now=int(hi['timestamp'],16); target=now-7*86400
lo=0; top=head
while lo<top:
 mid=(lo+top)//2; b=rpc('eth_getBlockByNumber',[hex(mid),False]); ts=int(b['timestamp'],16)
 if ts<target: lo=mid+1
 else: top=mid
b=rpc('eth_getBlockByNumber',[hex(lo),False]); print(json.dumps({'head':head,'head_utc':datetime.datetime.fromtimestamp(now,datetime.timezone.utc).isoformat(),'start':lo,'start_utc':datetime.datetime.fromtimestamp(int(b['timestamp'],16),datetime.timezone.utc).isoformat()}))
