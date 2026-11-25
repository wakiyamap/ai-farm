import json,subprocess

def rpc(m,p):
 x=subprocess.run(['python3','tools/rpc.py','ethereum',m,json.dumps(p)],capture_output=True,text=True,check=True)
 return json.loads(x.stdout)['result']
raw=rpc('eth_call',[{'to':'0x895879b2c1fbb6ccfcd101f2d3f3c76363664f92','data':'0xb0772d0b'},'latest'])
w=[raw[2+i:2+i+64] for i in range(0,len(raw)-2,64)]
for v in w[2:2+int(w[1],16)]:
 a='0x'+v[-40:]
 code=rpc('eth_getCode',[a,'latest'])
 try: name=rpc('eth_call',[{'to':a,'data':'0x06fdde03'},'latest'])
 except Exception as e: name='error:'+str(e)
 print(a,len(code)>2,len(name)>2,flush=True)
