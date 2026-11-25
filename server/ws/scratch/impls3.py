import json, subprocess
from collections import Counter
def rpc(method, params):
    out = subprocess.run(['python3','/srv/farm/ws/tools/rpc.py','ethereum',method,json.dumps(params)],
                         capture_output=True, text=True).stdout
    return json.loads(out).get('result')
a=json.load(open('scratch/mkts.json'))
c=Counter(); m={}
for x in a:
    code=(rpc('eth_getCode',[x,'latest']) or '0x')[2:]
    impl='0x'+code[20:60] if len(code)==90 else 'raw'
    c[impl]+=1; m.setdefault(impl,[]).append(x)
for k,v in c.items(): print(v, k, m[k][:3])
