import subprocess,json
RPC='/srv/farm/ws/tools/rpc.py'
for a,i in [('0x717170b66654292dfbd89c39f5ae6753d2ac1381',100),('0x717170b66654292dfbd89c39f5ae6753d2ac1381',300),('0x443366a7a5821619D8d57405511E4fadD9964771',100)]:
 for k,s in [('vault','0x9403b634'),('reward','0x11d850e8')]:
  p=subprocess.run(['python3',RPC,'ethereum','eth_call',json.dumps([{'to':a,'data':s+f'{i:064x}'},'latest'])],capture_output=True,text=True)
  o=json.loads(p.stdout);v=o.get('result')
  if v:v=[int(v[j:j+64],16) for j in range(2,len(v),64)]
  else:v=o.get('error',{}).get('message')
  print(a,i,k,v)
