import json,urllib.request,os
url=os.environ["RPC_RELAY_URL"]+"/ethereum?lane=research"
t0=os.environ["T0"]
head=int(os.environ["HEAD"],16)
def post(fb,tb,addrs):
    d={"jsonrpc":"2.0","id":1,"method":"eth_getLogs","params":[{"fromBlock":hex(fb),"toBlock":hex(tb),"address":addrs,"topics":[t0,None,None,None]}]}
    req=urllib.request.Request(url,data=json.dumps(d).encode(),headers={"content-type":"application/json"})
    r=urllib.request.urlopen(req)
    return json.loads(r.read())
f=head-126000
tot=0; hits=[]
for b in sorted(glob := [] ) or ["scratch/frax-x_aa.json","scratch/frax-x_ab.json","scratch/frax-x_ac.json"]:
    addrs=json.load(open(b))
    for i in range(9):
        fb,tb=f+i*14000,f+(i+1)*14000
        r=post(fb,tb,addrs)
        if "error" in r: print("ERR",r["error"].get("message","?")[:200],hex(fb)); continue
        logs=r.get("result") or []
        tot+=len(logs)
        if logs: print(len(logs),hex(fb),logs[0]["blockNumber"],logs[0]["transactionHash"][:14],logs[0]["topic0"])
print("total",tot)
