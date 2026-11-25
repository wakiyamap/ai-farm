import subprocess, json, sys
MC="0xe70E9185F5ea7Ba3C5d63705784D8563017f2E57"
T0=["0x90890809c654f11d6e72a28fa60149770a0d11ec6c92319d6ceb2bb0a4ea1a15",
    "0xf279e6a1f5e320cca91135676d9cb6e44ca8a08c0b88342bcdb1144f6511b568",
    "0xbb757047c2b5f3974fe26b7c10f732e7bce710b0952a71082702781e62ae0595"]
LATEST=134625848
FROM=LATEST-1344000  # 7 days at 0.45s/block
PAGE=4500
logs=[]
b=FROM
fails=0
while b<=LATEST:
    to=min(b+PAGE-1,LATEST)
    f={"address":MC,"topics":[T0],"fromBlock":hex(b),"toBlock":hex(to)}
    r=subprocess.run(["python3","/srv/farm/ws/tools/rpc.py","bsc","eth_getLogs",json.dumps([f])],capture_output=True,text=True)
    try:
        out=json.loads(r.stdout)
        if "result" in out: logs+=out["result"]
        else: fails+=1; print("FAIL",b,out.get("error",{}).get("message","?")[:120],file=sys.stderr)
    except Exception as e:
        fails+=1; print("ERR",b,r.stdout[:150],r.stderr[:150],file=sys.stderr)
    b=to+1
print("ranges scanned, fails:", (LATEST-F)//0 if False else "", fails, file=sys.stderr)
json.dump(logs,open("scratch/goose_logs7d.json","w"))
names={"0x90890809c654f11d6e72a28fa60149770a0d11ec6c92319d6ceb2bb0a4ea1a15":"Deposit",
"0xf279e6a1f5e320cca91135676d9cb6e44ca8a08c0b88342bcdb1144f6511b568":"Withdraw",
"0xbb757047c2b5f3974fe26b7c10f732e7bce710b0952a71082702781e62ae0595":"EmergencyWithdraw"}
from collections import Counter
c=Counter(names[l["topics"][0]] for l in logs)
users=Counter("0x"+l["topics"][1][-40:].lower() for l in logs)
print("total logs:",len(logs)); print(dict(c))
print("unique users:",len(users))
for u,n in users.most_common(8): print(u,n)
