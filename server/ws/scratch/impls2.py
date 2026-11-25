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
    if len(code)==90 and code[:20]=='363d3d373d3d3d363d' and code[62:]=='5af43d82803e903d91602b57fd5bf3':
        impl='0x'+code[22:62]
    else:
        impl='raw:'+str(len(code)//2)
    c[impl]+=1; m.setdefault(impl,[]).append(x)
for k,v in c.items(): print(v, k, m[k][:2])
