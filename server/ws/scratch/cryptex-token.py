import subprocess,json
RPC='/srv/farm/ws/tools/rpc.py'
for a in ['0x717170b66654292dfbd89c39f5ae6753d2ac1381','0x443366a7a5821619D8d57405511E4fadD9964771','0xc2Ba6B8E0EE3cf48B045D966F1dCda767df74833','0xA5b3Bb6e1f206624B3B8CE0c6A0f7614fd35Fa03','0xa8CcA36A624215a39D5af6854ac24868559424d3','0x2364536F4891Ed560A6728f4B36871de8176eE5c']:
 p=subprocess.run(['python3',RPC,'ethereum','eth_call',json.dumps([{'to':a,'data':'0x6ca2143c'},'latest'])],capture_output=True,text=True)
 v=json.loads(p.stdout)['result'];print(a,'0x'+v[-40:])
