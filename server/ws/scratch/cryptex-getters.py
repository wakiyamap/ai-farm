import subprocess,json,concurrent.futures
RPC='/srv/farm/ws/tools/rpc.py'
addrs=['0x717170b66654292dfbd89c39f5ae6753d2ac1381','0x443366a7a5821619D8d57405511E4fadD9964771','0xc2Ba6B8E0EE3cf48B045D966F1dCda767df74833','0xA5b3Bb6e1f206624B3B8CE0c6A0f7614fd35Fa03','0xa8CcA36A624215a39D5af6854ac24868559424d3','0x2364536F4891Ed560A6728f4B36871de8176eE5c']
getters={'collateral':'0xc6e1c7c9','counter':'0x61bc221a','paused':'0x5c975abb'}
def call(item):
 a,k,sel=item;p=subprocess.run(['python3',RPC,'ethereum','eth_call',json.dumps([{'to':a,'data':sel},'latest'])],capture_output=True,text=True)
 try:v=json.loads(p.stdout).get('result') or json.loads(p.stdout).get('error')
 except:v=p.stdout or p.stderr
 return a,k,v
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:
 for a,k,v in ex.map(call,[(a,k,sel) for a in addrs for k,sel in getters.items()]):print(a,k,v)
