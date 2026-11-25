import subprocess,json
pools=['0x8124cD94629Bd7e902D9B7dabDcef71F9847b232','0x9a2789dd698D010f3d6Bb5Bf865369A734D43f83','0xa649C9306896f90d6f8a3366f29be10557461144','0xC62D0265ADCe0719373661FFF26d93980f5e6Fc0','0xAc324adB90eDA530884eB0f5BE58614c6249484a','0x82Eb5b1F3A2286903F5918f8a42Cc84A2ea500fb','0x59aCef0FC104EDe425DF5CD3a1677A09e7e025cD']
def rpc(method,params):
 p=subprocess.run(['python3','/srv/farm/ws/tools/rpc.py','ethereum',method,json.dumps(params)],capture_output=True,text=True)
 if p.returncode: return {'error':p.stderr or p.stdout}
 return json.loads(p.stdout)
for addr in pools:
 c=rpc('eth_getCode',[addr,'latest']); q=rpc('eth_call',[{'to':addr,'data':'0x2f84cbf5'},'latest']);
 v=q.get('result','0x')[2:];words=[int(v[i:i+64],16) for i in range(0,len(v),64)]
 print(addr,'code',len(c.get('result','0x'))>2,'getter',bool(words),'amountOfSwaps',words[2] if len(words)>2 else None,'rewardUnits',words[10] if len(words)>10 else None,'rewardToken',hex(words[12]) if len(words)>12 else None,'error',q.get('error'))
from_block='0x1934c97';to_block='latest';f={'address':pools,'fromBlock':from_block,'toBlock':to_block}
r=rpc('eth_getLogs',[f]);print('v1_no_topic_count',len(r.get('result',[])),'error',r.get('error'))
f['topics']=['0x985cca3348e25076ac7404c08e594a15b8529496ecbf6b08af7fa24c5d4e742b'];r=rpc('eth_getLogs',[f]);print('v1_swap_count',len(r.get('result',[])),'error',r.get('error'))
