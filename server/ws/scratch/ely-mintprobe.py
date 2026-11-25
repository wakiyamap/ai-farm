#!/usr/bin/env python3
import json, os, subprocess, urllib.request as U
FORK="http://127.0.0.1:9009"
POOL="0x97796d80b6a1db78632f7451196b04f307329eb6"
USDC="0xb47c4C8F73F009CC0C0d3f92B388d13E293F0B65"
HYPE="0xba876237b0f021a6c6d852d6c26e107997cc5e81"
OWNER="0x00000000001a11ec000000000000000000000001"
SWAP="0x5b12abc7c91ef614710087f7db6c6734bd0184e5f964c0db87a04a68541ed3f9"
RESET=4549448
PARAM=2596148429267413814265248164610048
def sh(cmd):
    p=subprocess.run([str(x) for x in cmd],capture_output=True,text=True,timeout=300,
        env={**os.environ,"PATH":"/opt/foundry/bin:"+os.environ["PATH"]})
    out=(p.stdout+p.stderr).strip()
    if p.returncode!=0: raise RuntimeError(" ".join(map(str,cmd))+" rc\n"+out[-300:])
    return out
def jrpc(method,params=()):
    body=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    r=json.loads(U.urlopen(U.Request(FORK,data=body,headers={"content-type":"application/json"}),timeout=120).read())
    if "error" in r: raise RuntimeError(method+": "+json.dumps(r["error"])[:200])
    return r["result"]
def i2(x,signed=False): return int.from_bytes(bytes.fromhex(x[2:]),"big",signed=signed) if x and x!="0x" else 0
def warm(): sh(["fork","fund-token","elysium",USDC,POOL,OWNER,"1"])
def fcal(fn,args):
    sel=sh(["cast","sig",fn]).strip()
    return sel+sh(["cast","abi-encode",fn]+[str(a) for a in args]).strip()[2:]
def send(frm,to,data,tag):
    out=sh(["fork","send","elysium",json.dumps({"from":frm,"to":to,"data":data,"value":"0x0","gas":"0x4c4b20"})])
    st='"status": "0x1"' in out.replace("\n"," ")
    print(f"{tag}: {'OK' if st else 'REVERT'}")
    import re
    m=re.search(r'"revertReason": "([^"]*)"',out); print("  revertReason:",m.group(1) if m else "-")
    m=re.search(r'"logs": (\[[^\n]*?\])',out); print("  logs:",m.group(1)[:120] if m else "-")
    th=re.search(r'"transactionHash": "(0x[0-9a-f]{64})"',out)
    return st,out,(th.group(1) if th else None)
sh(["fork","lease","elysium","12","mint revert probe"])
sh(["fork","reset","elysium",RESET])
sh(["fork","fund","elysium",OWNER,"20"]); warm()
cargs=sh(["cast","abi-encode","constructor(address,address,address)",POOL,USDC,HYPE]).strip()
dep=sh(["fork","deploy","elysium","scratch/elysium-lpfee/contracts/out/ElysiumLpFee.sol/ElysiumLpFee.json",OWNER,"--args",cargs])
EX=[w for w in dep.split() if w.startswith("0x") and len(w)==42][0]
sh(["fork","fund","elysium",OWNER,"20"])
sh(["fork","fund-token","elysium",USDC,POOL,EX,"30_000_000_000".replace("_","")])
sh(["fork","fund-token","elysium",HYPE,POOL,EX,"5_000_000_000_000_000_000".replace("_","")])
t=i2("0x"+jrpc("eth_call",[{"to":POOL,"data":"0x3850c7bd"},"latest"])[2:][64:128],signed=True)
print("tick",t)
cal=fcal("mintLiquidity(int24,int24,uint128,bytes)",[233700,233800,PARAM,"0x"])
st,out,th=send(OWNER,EX,cal,"mint param scale")
if th:
    tr=sh(["fork","trace","elysium",th])
    try:
        fr=json.loads(tr[tr.index("["):tr.rindex("]")+1])
        def walk(f,d=0):
            err=f.get("error") or {}
            print("  "*d,f.get("type"),f.get("from","-")[6:] if isinstance(f.get("from"),str) else f.get("from","-"),"->",f.get("to","-")[6:] if isinstance(f.get("to"),str) else f.get("to","-"),
                  "err:",err if err else "-","in:",str(f.get("input"))[:140] if f.get("input") else "-")
            for c in f.get("calls",[]) or []: walk(c,d+1)
        for x in fr: walk(x)
    except Exception as e: print("trace parse:",e,tr[-300:])
st2,out2,th2=send(OWNER,EX,fcal("mintLiquidity(int24,int24,uint128,bytes)",[233700,233800,PARAM//10,"0x"]),"mint param/10")
sh(["fork","release","elysium"])
