import json,urllib.request,os
url=os.environ["RPC_RELAY_URL"]+"/ethereum?lane=research"
t0="0x"+os.environ["T0"][2:]
head=0x1924268
def post(p):
    d={"jsonrpc":"2.0","id":1,"method":"eth_getLogs","params":[{"fromBlock":p[0],"toBlock":p[1],"address":p[2],"topics":[p[3]]}]}
    r=urllib.request.urlopen(urllib.request.Request(url,json.dumps(d).encode(),{"content-type":"application/json"}))
    return json.loads(r.read())
blocks=[]
f=head-126000
for i in range(9):
    blocks.append([hex(f+i*14000),hex(f+(i+1)*14000)])
tot=0
for b in ["ls /dev/null","scratch/frax-b2.json","scratch/frax-b3.json"]:
    addrs=json.load(open(b))
    for (fb,tb) in blocks:
        r=post((fb,tb,addrs,[t0,None,None,None]))
        if "error" in r: print("ERR",r["error"]["message"][:80],fb)
        logs=r.get("result") or []
        tot+=len(logs)
        if logs: print(b[-6:],fb,tb,len(logs))
print("total",tot)
