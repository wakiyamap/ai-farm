import json, subprocess, os, re
WS="/srv/farm/ws"
ENV=dict(os.environ, PATH="/opt/farm/bin:/opt/foundry/bin:"+os.environ.get("PATH",""))
def sh(*c):
    r=subprocess.run(c, capture_output=True, text=True, env=ENV)
    if r.returncode!=0 or "FAILED" in r.stdout: raise SystemExit("FAILED %s: %s"%(c[:3],r.stdout[-200:]))
    return r.stdout.strip()
import urllib.request
def rpc(method, params, soft=False):
    body=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    req=urllib.request.Request("http://127.0.0.1:9003",data=body,headers={"content-type":"application/json"})
    out=json.loads(urllib.request.urlopen(req,timeout=180).read())
    if "error" in out:
        if soft: return out["error"]
        raise SystemExit("RPC %s: %s"%(method,out["error"]))
    return out["result"]
FOLIO="0x2cf4dafc17e163abd6770e1794e1ad10deb7d32e"; SELL="0x060505527c83e8bfeb9b4ff08248b82e688800f1"
BUY="0xf404e5f887dbd5508e16a1198fcdd5de1a4296b8"; WINNER="0xd98d34008d1bbb29013592c637f8e9fca4179fa0"
OWNER="0x000000000000000000000000000000000000f007"; SELL_AMT=57582275034043643305; U=9_057_578
def w(v): return hex(v)[2:].zfill(64)
def addr_word(a): return a[2:].lower().rjust(64,"0")
leg1=open(WS+"/scratch/dtf92-swap1.txt").read().strip(); legf=open(WS+"/scratch/dtf92-swap2.txt").read().strip()
PAYFULL=int(open(WS+"/scratch/rf-venue19-result.json").read() and json.load(open(WS+"/scratch/rf-venue19-result.json"))["PAYFULL"])
SIG="fundSwapAndBid(address,uint256,address,address,uint256,uint256,uint256,uint256,bytes,bytes,bytes,uint256)"
sel=sh("cast","sig",SIG)
def fsb(mp,mo,mb,f,l1):
    enc=sh("cast","abi-encode","f(address,uint256,address,address,uint256,uint256,uint256,uint256,bytes,bytes,bytes,uint256)",
        FOLIO,"8",SELL,BUY,str(U),str(mo),str(SELL_AMT),str(mb),f,l1,"0x",str(mp))
    return sel+enc[2:]
cal=fsb(0,PAYFULL,PAYFULL,legf,leg1)
e=rpc("eth_call",[{"from":OWNER,"to":WINNER,"data":cal},"latest"],soft=True)
print("TOP:", str(e)[:300])
tr=rpc("debug_traceCall",[{"from":OWNER,"to":WINNER,"data":cal,"gas":"0x989680","value":"0x0"},"latest",{"tracer":"callTracer"}],soft=True)
json.dump(tr,open(WS+"/scratch/rf-venue20-trace.json","w"))
def walk(n,d=0):
    err=n.get("error")
    mark="ERR" if err else "   "
    print("  "*d+mark, n.get("type",""), n.get("from","")[:12], "->", n.get("to","")[:12], (n.get("input") or "")[:10], (err or "")[:120])
    for c in n.get("calls",[]): walk(c,d+1)
res=tr.get("result",tr) if isinstance(tr,dict) else tr
if isinstance(res,dict): walk(res)
else: print("TRACE:", str(tr)[:200])
