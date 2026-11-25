import json,urllib.request,os
url=os.environ["RPC_RELAY_URL"]+"/ethereum?lane=research"
t0=os.environ["T0V1"]
head=int(os.environ["HEAD"],16)
def post(fb,tb,addrs):
    d={"jsonrpc":"2.0","id":1,"method":"eth_getLogs","params":[{"fromBlock":hex(fb),"toBlock":hex(tb),"address":addrs,"topics":[t0,None,None,None]}]}
    req=urllib.request.Request(url,data=json.dumps(d).encode(),headers={"content-type":"application/json"})
    return json.loads(urllib.request.urlopen(req,timeout=15).read())
f=head-126000
all_logs=[]
for b in ["scratch/frax-x_aa.json","scratch/frax-x_ab.json","scratch/frax-x_ac.json"]:
    addrs=json.load(open(b))
    for i in range(9):
        fb,tb=f+i*14000,f+(i+1)*14000
        r=post(fb,tb,addrs)
        if "error" in r:
            msg=r["error"]["message"][:40]
            print("ERR",msg,fb); continue
        logs=r.get("result") or []
        all_logs+=logs
print("total 30d:",len(all_logs))
for l in all_logs[:5]:
    print(l["address"][:10],int(l["blockNumber"],16),l["transactionHash"][:18],"topics",len(l["topics"]))
json.dump(all_logs,open("scratch/frax-v1-hits.json","w"))
