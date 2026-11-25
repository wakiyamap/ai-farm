import json,urllib.request,os
url=os.environ["RPC_RELAY_URL"]+"/ethereum?lane=research"
t0=os.environ["T0"]
def post(fb,tb,addrs):
    p={"fromBlock":hex(fb),"toBlock":hex(tb),"address":addrs,"topics":[t0,None,None,None]}
    d={"jsonrpc":"2.0","id":1,"method":"eth_getLogs","params":[p]}
    req=urllib.request.Request(url,data=json.dumps(d).encode(),headers={"content-type":"application/json"})
    return json.loads(urllib.request.urlopen(req).read())
wins=[(25000000,25030000),(25400000,25430000),(25800000,25830000),(26050000,26080000)]
tot=0
for b in ["scratch/frax-x_aa.json","scratch/frax-x_ab.json","scratch/frax-x_ac.json"]:
    addrs=json.load(open(b))
    for fb,tb in wins:
        r=post(fb,tb,addrs)
        if "error" in r: print("ERR",r["error"]["message"][:60],fb); continue
        logs=r.get("result") or []
        tot+=len(logs)
        if logs: print(len(logs),"chunk",fb,logs[0]["transactionHash"][:16],"ntop",len(logs[0]["topics"]),"datalen",len(logs[0]["data"]))
print("total",tot)
