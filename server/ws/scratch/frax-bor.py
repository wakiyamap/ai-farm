import json,urllib.request,os
url=os.environ["RPC_RELAY_URL"]+"/ethereum?lane=research"
sel="0x"+ "12f5670a472f9d766e5e42e0c0c47a9065f5c10305821e41571c401e0205420f"[0:0] # placeholder
import subprocess
sel=subprocess.run(["cast","keccak","totalBorrow()"],capture_output=True,text=True).stdout.strip()
addrs=[a for l in open("scratch/frax-all.txt") for a in [l.strip()] if len(a)==42]
out=[]
for i,a in enumerate(addrs):
    d={"jsonrpc":"2.0","id":1,"method":"eth_call","params":[{"to":a,"data":sel},"latest"]}
    req=urllib.request.Request(url,data=json.dumps(d).encode(),headers={"content-type":"application/json"})
    try: r=json.loads(urllib.request.urlopen(req,timeout=10).read())
    except Exception as e: print("ERR",a,e); continue
    v=r.get("result")
    if not v or "error" in r: print("err",a,r.get("error",{}).get("message","")[:40]); continue
    n=int(v,16) if v!="0x" else 0
    if n>10**11: out.append((a,n/10**18))
out.sort(key=lambda x:-x[1])
json.dump(out,open("scratch/frax-borrows.json","w"))
for a,b in out[:10]: print(f"{a} {b:,.0f}")
print("markets with borrow>=1e11:",len(out))
