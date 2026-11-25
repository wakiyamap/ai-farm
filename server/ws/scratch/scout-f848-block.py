import json, subprocess, datetime
target=1794874294
lo,hi=51400000,51500000
while lo<hi:
 m=(lo+hi)//2
 p=subprocess.run(['python3','/srv/farm/ws/tools/rpc.py','hyperevm','eth_getBlockByNumber',json.dumps([hex(m),False])],capture_output=True,text=True)
 if p.returncode: print(p.stderr); break
 b=json.loads(p.stdout)['result']; ts=int(b['timestamp'],16)
 if ts<target:lo=m+1
 else:hi=m
print(lo,datetime.datetime.fromtimestamp(ts,datetime.timezone.utc),ts,target)
