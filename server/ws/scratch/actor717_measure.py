import json
import subprocess
from datetime import datetime, timezone

R = '/srv/farm/ws/tools/rpc.py'
A = '0x717230408d12cb4892f3150eab051dbfa66a19ad'
T = [
 '0x01a91968dbc98b9f0d357080925ce1d73978c3ef19c6fdfb4807695525b35d4b',
 '0x33f4694eee54fdc292cec90f55a93008c13358b8ea1a33ba4b14b3d20cd29af4',
 '0xe744f8a7030a5930ee682399ee92e7ddef1065d23a0bc5dae34fc667b188c843',
 '0xd95c5a5157081c5fda0f40f61c59adc3248cd4b65991aa366f1228c795c1a2d0',
]
def rpc(m,p):
 x=subprocess.run(['python3',R,'hyperevm',m,json.dumps(p)],capture_output=True,text=True,check=True)
 return json.loads(x.stdout)['result']
def i(x):return int(x,16)
head=rpc('eth_getBlockByNumber',['latest',False]); hi=i(head['number']); now=i(head['timestamp']); target=now-7*86400
lo=max(0,hi-800000)
while lo+1<hi:
 mid=(lo+hi)//2; ts=i(rpc('eth_getBlockByNumber',[hex(mid),False])['timestamp'])
 if ts<target:lo=mid
 else:hi=mid
start=rpc('eth_getBlockByNumber',[hex(hi),False])
print('window',hi,datetime.fromtimestamp(i(start['timestamp']),timezone.utc).isoformat(),i(head['number']),datetime.fromtimestamp(now,timezone.utc).isoformat(),flush=True)
for h in T:
 tx=rpc('eth_getTransactionByHash',[h]); rec=rpc('eth_getTransactionReceipt',[h]); bn=i(rec['blockNumber']); gas=i(rec['gasUsed'])*i(rec['effectiveGasPrice'])/1e18
 before=i(rpc('eth_getBalance',[A,hex(bn-1)]))/1e18; after=i(rpc('eth_getBalance',[A,hex(bn)]))/1e18
 payout=after-before+gas
 print(json.dumps(dict(tx=h,block=bn,time=datetime.fromtimestamp(i(tx['blockNumber']) and i(rpc('eth_getBlockByNumber',[hex(bn),False])['timestamp']),timezone.utc).isoformat(),gas_hype=gas,balance_delta_hype=after-before,estimated_native_payout_hype=payout,gas_used=i(rec['gasUsed']),gas_price_gwei=i(rec['effectiveGasPrice'])/1e9,status=i(rec['status']),selector=tx['input'][:10])),flush=True)
