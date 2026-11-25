import subprocess,json,datetime
RPC='/srv/farm/ws/tools/rpc.py'
def block(num):
 p=subprocess.run(['python3',RPC,'ethereum','eth_getBlockByNumber',json.dumps([num,False])],capture_output=True,text=True)
 if p.returncode: raise RuntimeError(p.stderr)
 b=json.loads(p.stdout)['result']; return int(b['number'],16),int(b['timestamp'],16)
p=subprocess.run(['python3',RPC,'ethereum','eth_blockNumber','[]'],capture_output=True,text=True,check=True)
head=int(json.loads(p.stdout)['result'],16)
head,ts=block(hex(head)); target=ts-7*86400
lo=max(0,head-100000);hi=head
while lo<hi:
 mid=(lo+hi)//2
 _,t=block(hex(mid))
 if t<target:lo=mid+1
 else:hi=mid
for b in [lo,head]:
 n,t=block(hex(b));print(n,hex(n),datetime.datetime.fromtimestamp(t,datetime.timezone.utc).isoformat())
