import json,urllib.request,os
from collections import Counter
url=os.environ['RPC_RELAY_URL']
def rpc(method,params):
    body=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    r=urllib.request.urlopen(url.rstrip('/')+'/ethereum?lane=research', body, timeout=90)
    return json.load(r)
T0='0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
FB='0x000000000000000000000000c59b0e4de5f1248c1140964e0ff287b192407e0c'
c=Counter(); em=Counter(); lot=Counter()
for a in range(26109933,26369933,330000):
    b=min(a+330000-1,26369933)
    r=rpc('eth_getLogs',[{"topics":[T0,FB],"fromBlock":hex(a),"toBlock":hex(b)}])
    if isinstance(r.get('error'),dict): print('ERR',r['error'].get('message')); break
    for l in r.get('result') or []:
        c['->0x'+l['topics'][2][-40:].lower()]+=1
        em[l['address']]+=1
        v=int(l['data'],16)
        lot['0x'+l['topics'][2][-40:].lower()]+=v//10**6 if v>10**6 else 0
print('recipients:',c.most_common(12))
print('token emitters:',em.most_common(8))
