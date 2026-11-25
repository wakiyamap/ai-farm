import json, subprocess, collections
RPC='/srv/farm/ws/tools/rpc.py'
def call(method, params):
 p=subprocess.run(['python3',RPC,'ethereum',method,json.dumps(params)],capture_output=True,text=True)
 if p.returncode: raise RuntimeError(p.stderr+' '+p.stdout)
 o=json.loads(p.stdout)
 if 'error' in o: raise RuntimeError(str(o['error']))
 return o['result']
addresses=['0x0000000000861109794c3C214B61A2B500f49ed2','0x0000000000B6ECC19F9d3dCC78Dd486230f38af2','0x000000000023D3afBd1D8305ffaC74860b5C36e4','0x0000000000d8858E1A9B373582A691dB992C23CA']
start,head=26430035,26480279
for a in addresses:
 code=call('eth_getCode',[a,'latest'])
 pool=call('eth_call',[{'to':a,'data':'0x7535d246'},'latest'])
 ctr=collections.Counter(); count=0; samples=[]
 for first in range(start,head+1,5000):
  chunk=call('eth_getLogs',[{'address':a,'fromBlock':hex(first),'toBlock':hex(min(first+4999,head))}])
  count+=len(chunk)
  ctr.update(x['topics'][0] if x['topics'] else 'no_topic' for x in chunk)
  samples.extend(chunk[:2])
 print(json.dumps({'address':a,'code_bytes':(len(code)-2)//2,'pool':pool,'logs_7d':count,'topics':ctr,'sample_tx':[x['transactionHash'] for x in samples[:5]]}),flush=True)
# Same-shape positive control: address plus topic, 1000-block range.
transfer=subprocess.check_output(['/opt/foundry/bin/cast','keccak','Transfer(address,address,uint256)'],text=True).strip()
ctl=call('eth_getLogs',[{'address':'0x7f39C581F595B53c5cb19bD0b3f8dA6c935E2Ca0','topics':[transfer],'fromBlock':hex(head-999),'toBlock':hex(head)}])
print(json.dumps({'control':'wstETH Transfer','range':[head-999,head],'count':len(ctl),'first_tx':ctl[0]['transactionHash'] if ctl else None}),flush=True)
