import json, urllib.request, os
RELAY=os.environ['RPC_RELAY_URL']; HEAD=26363073
addr='0xae05Cd22df81871bc7cC2a04BeCfb516bFe332C8'.lower()
body=json.dumps({"jsonrpc":"2.0","id":1,"method":"eth_getLogs","params":[{"address":[addr],"fromBlock":hex(HEAD-40000),"toBlock":hex(HEAD)}]}).encode()
req=urllib.request.Request(f"{RELAY}/ethereum?lane=research",data=body,headers={'content-type':'application/json'})
r=json.loads(urllib.request.urlopen(req,timeout=30).read())
logs=r.get('result') or []
print('error', r.get('error'))
print('any-events in 40k blocks:',len(logs))
from collections import Counter
c=Counter(lg['topics'][0] for lg in logs)
for t,n in c.most_common(8): print(t[:40],n)
