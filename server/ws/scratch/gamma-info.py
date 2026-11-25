import json, subprocess, tempfile, os, sys

def rpc(method, params):
    f=tempfile.NamedTemporaryFile("w",suffix=".json",delete=False)
    json.dump(params,f); f.close()
    r=subprocess.run(["python3","tools/rpc.py","polygon",method,"--params-file",f.name],capture_output=True,text=True)
    os.unlink(f.name)
    d=json.loads(r.stdout)
    if "error" in d: print("ERR",json.dumps(d["error"])[:200]); sys.exit(1)
    return d["result"]

def words(h):
    h=h[2:] if h.startswith("0x") else h
    return [h[i:i+64] for i in range(0,len(h),64)]

def decode_results(hexres):
    w=words(hexres)
    n=int(w[1],16); base=2; out=[]
    for k in range(n):
        off=int(w[base+k],16)//32; p=base+off
        succ=int(w[p],16); boff=int(w[p+1],16)//32; q=p+boff
        blen=int(w[q],16)
        data=w[q+1] if blen>=32 else None
        out.append((succ,data))
    return out

vaults=json.load(open("scratch/gamma-vaults.json"))
MC="0xcA11bde05977b3631167028862bE2a173976CA11"
calls=[]
for name,a in vaults:
    calls.append(f"({a},true,0x8da5cb5b)")   # owner()
    calls.append(f"({a},true,0x18160ddd)")   # totalSupply()
r=subprocess.run(["cast","calldata","aggregate3((address,bool,bytes)[])","[" + ",".join(f"({a},true,0x{d})" for name,a in vaults for d in ["8da5cb5b","18160ddd"]) + "]"],capture_output=True,text=True)
cd=r.stdout.strip()
res=rpc("eth_call",[{"to":MC,"data":cd},"latest"])
out=decode_results(res)
info=[]
owners={}
for i,(name,a) in enumerate(vaults):
    s_o,d_o=out[2*i]; s_t,d_t=out[2*i+1]
    owner="0x"+d_o[-40:] if (s_o and d_o) else None
    ts=int(d_t,16) if (s_t and d_t) else 0
    info.append({"name":name,"vault":a,"owner":owner,"totalSupply":ts})
    owners[owner]=owners.get(owner,0)+1
json.dump(info,open("scratch/gamma-vault-info.json","w"))
print("owners:")
for o,c in sorted(owners.items(),key=lambda x:-x[1])[:12]:
    print(" ",o,c)
live=[x for x in info if x["totalSupply"]>0]
print("live vaults (supply>0):",len(live))
bn=rpc("eth_getBlockByNumber",["latest",False])
print("latest",int(bn["number"],16),"ts",int(bn["timestamp"],16))
