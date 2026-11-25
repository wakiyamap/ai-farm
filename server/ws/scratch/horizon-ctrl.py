import json, urllib.request, os
RELAY=os.environ['RPC_RELAY_URL']; HEAD=26363073
TOPIC='0xe413a321e8681d831f4dbccbca790d2952b56f977908e45be37335533e005286'
ctrl={'aave_v3':'0x87870bca3f3fd6335c3f4ce8392d69350b4fa4e2','aave_v2':'0x7d2768de32b0b80b7a3454c06bdac94a69ddc7a9'}
for name,addr in ctrl.items():
    n=0
    for i in range(4):
        f=HEAD-i*10000+1; t=HEAD-(i-1)*10000 if i>0 else HEAD
        body=json.dumps({"jsonrpc":"2.0","id":1,"method":"eth_getLogs","params":[{"address":[addr.lower()],"topics":[[TOPIC]],"fromBlock":hex(f),"toBlock":hex(t)}]}).encode()
        req=urllib.request.Request(f"{RELAY}/ethereum?lane=research",data=body,headers={'content-type':'application/json'})
        r=json.loads(urllib.request.urlopen(req,timeout=30).read())
        logs=r.get('result') or []
        n+=len(logs)
        if logs and i==0:
            lg=logs[-1]; d=lg['data']; print('ctrl first', name, int(lg['blockNumber'],16), int(d[64:128],16))
    print(name,'events in last 40k blocks:',n)
