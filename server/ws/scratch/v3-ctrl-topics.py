import json, urllib.request, os
RELAY=os.environ['RPC_RELAY_URL']; HEAD=26363073
for name,addr in [('aave_v3','0x87870bca3f3fd6335c3f4ce8392d69350b4fa4e2')]:
    body=json.dumps({"jsonrpc":"2.0","id":1,"method":"eth_getLogs","params":[{"address":[addr],"fromBlock":hex(HEAD-20000),"toBlock":hex(HEAD)}]}).encode()
    req=urllib.request.Request(f"{RELAY}/ethereum?lane=research",data=body,headers={'content-type':'application/json'})
    r=json.loads(urllib.request.urlopen(req,timeout=30).read())
    logs=r.get('result') or []
    from collections import Counter
    c=Counter(lg['topics'][0] for lg in logs)
    print(name,'n',len(logs)); 
    for t,n in c.most_common(8): print(' ',t,n)
