import subprocess,json,concurrent.futures
RPC='/srv/farm/ws/tools/rpc.py'
addrs=['0x717170b66654292dfbd89c39f5ae6753d2ac1381','0x443366a7a5821619D8d57405511E4fadD9964771','0xc2Ba6B8E0EE3cf48B045D966F1dCda767df74833','0xA5b3Bb6e1f206624B3B8CE0c6A0f7614fd35Fa03','0xa8CcA36A624215a39D5af6854ac24868559424d3','0x2364536F4891Ed560A6728f4B36871de8176eE5c']
counts=[625,201,115,6,7,4]
items=[]
for a,n in zip(addrs,counts):
 for i in sorted(set([1,2,max(1,n-2)])):
  items.extend([(a,i,'vault','0x9403b634'),(a,i,'reward','0x11d850e8'),(a,i,'req','0xde9952c9')])
def call(item):
 a,i,k,sel=item;data=sel+f'{i:064x}'
 p=subprocess.run(['python3',RPC,'ethereum','eth_call',json.dumps([{'to':a,'data':data},'latest'])],capture_output=True,text=True)
 try:v=json.loads(p.stdout).get('result') or json.loads(p.stdout).get('error')
 except:v=p.stdout or p.stderr
 if isinstance(v,str) and v.startswith('0x'):
  words=[int(v[j:j+64],16) for j in range(2,len(v),64)];v=words
 return a,i,k,v
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
 for a,i,k,v in ex.map(call,items):print(a,i,k,v)
