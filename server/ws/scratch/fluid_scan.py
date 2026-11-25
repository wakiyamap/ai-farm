import json, subprocess, time, collections
TOPIC="0x80fd9cc6b1821f4a510e45ffce6852ea3404807b5d3d833ffa85664408afcb66"
ADDRS=["0xdf16adaf80584b2723f3ba1eb7a601338ba18c4e","0xf2c8f54447cbd591c396b0dd7ac15faf552d0fa4","0xa0f83fc5885cebc0420ce7c7b139adc80c4f4d91","0xf55b8e9f0c51ace009f4b41d03321675d4c643b3"]
NODE="https://polygon-bor-rpc.publicnode.com"
START, END, PAGE = 96644000, 97550672, 10000
logs=[]; pages=0; fails=[]
b=START
while b<=END:
    e=min(b+PAGE-1,END)
    body=json.dumps({"jsonrpc":"2.0","id":1,"method":"eth_getLogs","params":[{"address":ADDRS,"topics":[TOPIC],"fromBlock":hex(b),"toBlock":hex(e)}]})
    ok=False
    for attempt in range(3):
        p=subprocess.run(["curl","-s","-m","40","-H","Content-Type: application/json","-X","POST",NODE,"-d",body],capture_output=True,text=True)
        try:
            d=json.loads(p.stdout)
            if "result" in d: logs+=d["result"]; ok=True; break
            fails.append((b,str(d.get("error"))[:120]))
        except Exception as ex: fails.append((b,p.stdout[:120]))
        time.sleep(2)
    pages+=1; b=e+1
print("pages",pages,"logs",len(logs),"fails",len(fails))
if fails[:3]: print("sample fails",fails[:3])
nt=collections.Counter(len(l["topics"]) for l in logs)
print("topic counts",dict(nt))
t1=collections.Counter(l["topics"][1].lower() for l in logs if len(l["topics"])>1)
print("DISTINCT TAKERS",len(t1))
for k,v in t1.most_common(): print(" ",k,v)
byv=collections.Counter(l["address"].lower() for l in logs)
import itertools
short=[l for l in logs if len(l["topics"])<2]
print("short logs",len(short),[ (hex(int(l["blockNumber"],16)),l["address"][:10]) for l in short[:6]])
print("BY VAULT",dict(byv))
bn=[int(l["blockNumber"],16) for l in logs]
print("blocks",min(bn) if bn else '-',max(bn) if bn else '-')
json.dump(logs,open("/srv/farm/ws/scratch/logs7d_fresh.json","w"))
