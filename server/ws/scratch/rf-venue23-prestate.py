import json, subprocess, os
WS="/srv/farm/ws"
ENV=dict(os.environ, PATH="/opt/farm/bin:/opt/foundry/bin:"+os.environ.get("PATH",""))
def sh(*c):
    r=subprocess.run(c, capture_output=True, text=True, env=ENV)
    if r.returncode!=0: raise SystemExit("FAILED %s"%c[:3])
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
def addr_word(a): return a[2:].lower().rjust(64,"0")
leg1=open(WS+"/scratch/dtf92-swap1.txt").read().strip(); legf=open(WS+"/scratch/dtf92-swap2.txt").read().strip()
PAYFULL=9398683583154130380
SIG="fundSwapAndBid(address,uint256,address,address,uint256,uint256,uint256,uint256,bytes,bytes,bytes,uint256)"
sel=sh("cast","sig",SIG)
def fsb(mp,mo,mb,f,l1):
    enc=sh("cast","abi-encode","f(address,uint256,address,address,uint256,uint256,uint256,uint256,bytes,bytes,bytes,uint256)",
        FOLIO,"8",SELL,BUY,str(U),str(mo),str(SELL_AMT),str(mb),f,l1,"0x",str(mp))
    return sel+enc[2:]
cal=fsb(0,10**15,PAYFULL,legf,leg1)
tr=rpc("debug_traceCall",[{"from":OWNER,"to":WINNER,"data":cal,"gas":"0x989680","value":"0x0"},"latest",
    {"tracer":"prestateTracer","tracerConfig":{"diffMode":True}}],soft=True)
res=tr.get("result",tr) if isinstance(tr,dict) else tr
json.dump(res,open(WS+"/scratch/rf-venue23-prestate.json","w"),indent=1)
print(type(res), list(res.keys())[:6] if isinstance(res,dict) else str(res)[:200])
tokens={"SELL":SELL,"BUY":BUY,"USDC":"0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"}
def tokencall(token,fn,who):
    return int(rpc("eth_call",[{"to":token,"data":fn+addr_word(who)},"latest"]),16)
def balof(acct, token):
    # read pre/post storage: prestate gives accounts with balances of native only; token balances need eth_getStorageAt? For ERC20 proxy read via eth_call with 'pre' block impossible. Instead compare balanceOf now (after trace, trace does not persist state)
    pass
accts=res.get("post",{}) if isinstance(res,dict) else {}
pre=res.get("pre",{}) if isinstance(res,dict) else {}
for a in list(accts.keys())[:40]:
    b0=pre.get(a,{}).get("balance",0) if isinstance(pre.get(a,{}),dict) else 0
    b1=accts.get(a,{}).get("balance",0) if isinstance(accts.get(a),dict) else 0
    print(a[:14], "native", int(b0) if isinstance(b0,str)==False else 0, "->", int(b1))
