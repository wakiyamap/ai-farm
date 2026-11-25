import json, subprocess, os, re, sys
WS="/srv/farm/ws"
RESET=26306742
FOLIO="0x2cf4dafc17e163abd6770e1794e1ad10deb7d32e"
FOLIOB="0xe592f69e4f60e9a78dba0043573b898386c01cb8"
SELL="0x060505527c83e8bfeb9b4ff08248b82e688800f1"
BUY="0xf404e5f887dbd5508e16a1198fcdd5de1a4296b8"
SWAPPER="0x6131b5fae19ea4f9d964eac0408e4408b66337b5"
WINNER="0xd98d34008d1bbb29013592c637f8e9fca4179fa0"
VAULT="0x8f10b468b06c6fd214b65f87778827f7d113f996"
AGVROUTER="0x111111125421ca6dc452d289314280a0f8842a65"
FUNROUTER="0xA043FDc5A6E2E381e3532d5A97404b82fb7A0af8"
AGV1111="0x1111110f0f73c0b2ef09ec012eae758b3e03a902"
MOD="0xa88cd6b934c64ea830b78967b2f8a0de91577edc"
USDC="0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"
USDC_HOLDER="0x98c23e9d8f34fefb1b7bd6a91b7ff122f4e16f5c"
SELL_AMT=57582275034043643305
SELL_FUND=SELL_AMT
BUY_FUND=8*10**18
RT_PULL=15_610_000_000_000_000_000
U=9_057_578
OWNER=re.search(r'OWNER = "(0x[0-9a-f]+)"', open(WS+"/scratch/rf-venue-proof13.py").read()).group(1)
SETTLE="0x2b7727076b9c9b1834a2f95b81f12eedd30db9f1"
WRAP="0xebbcb2cee51c2fee4062c9c1270dcb98b0b22250"
ADMIN="0x3715b2154d2ff4c5b027c7a1f734b53f27bc34f1"
REQ=1794573000; OFF=1794572444
ART="scratch/reserve-folio-dtf-ethereum/contracts/out/FolioBidV3.sol/FolioBidV3.json"
ENV=dict(os.environ, PATH="/opt/farm/bin:/opt/foundry/bin:"+os.environ.get("PATH",""))
def sh(*c):
    r=subprocess.run(c, capture_output=True, text=True, env=ENV)
    if r.returncode!=0 or "FAILED" in r.stdout: raise SystemExit("FAILED %s: %s%s"%(c[:3],r.stdout[-200:],r.stderr[-200:]))
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
def w(v): return hex(v)[2:].zfill(64)
def addr_word(a): return a[2:].lower().rjust(64,"0")
def bal(token, who): return int(rpc("eth_call",[{"to":token,"data":"0x70a08231"+addr_word(who)},"latest"]),16)
def norm(res):
    s=str(res.get("status")); return "0x1" if s in ("0x1","1") else "0x0"
def keccak(hb): return sh("cast","keccak",hb)[2:]
def addr_of(dep): return [t for t in dep.split() if t.startswith("0x") and len(t)==42][0]
def send(to,calldata,frm=None):
    return json.loads(sh("fork","send","ethereum",json.dumps({"from":frm or OWNER,"to":to,"data":calldata,"gas":"0x989680","value":"0x0"})))
print("OWNER", OWNER, len(OWNER))
import atexit
st0=sh("fork","status"); print(st0)
print(sh("fork","lease","ethereum","15","venue26 settle with swapped leg roles"))
print(sh("fork","reset","ethereum",str(RESET)))
import sys
r0=rpc("anvil_setBlockTimestampInterval",["0x0"],soft=True)
print("interval0:", str(r0)[:120])
print(sh("fork","status"))
atexit.register(lambda: sh("fork","release","ethereum"))
sh("fork","fund","ethereum",OWNER,"2")
ts0=int(rpc("eth_getBlockByNumber",[hex(RESET),False])["timestamp"],16)
enc=sh("cast","abi-encode","f(uint256,address,address,uint256)","8",SELL,BUY,str(SELL_AMT))
PAYFULL=int(rpc("eth_call",[{"to":FOLIO,"data":"0x76990dcd"+enc[2:]},"latest"])[66:130],16)
print("PAYFULL",PAYFULL)
a=sh("cast","abi-encode","f(address,address,address)",SWAPPER,FOLIO,FOLIOB)
E=addr_of(sh("fork","deploy","ethereum",ART,OWNER,"--args",a))
codeE=rpc("eth_getCode",[E,"latest"]); assert len(codeE)>2000
slot=None
for s in range(8):
    loc="0x"+keccak("0x"+addr_word(FOLIO)+w(s))
    if int(rpc("eth_getStorageAt",[E,loc,"latest"]),16)==1: slot=s;break
assert slot is not None
locA="0x"+keccak("0x"+addr_word(FOLIO)+w(slot)); locB="0x"+keccak("0x"+addr_word(FOLIOB)+w(slot))
sh("fork","fund","ethereum",WINNER,"1")
rpc("anvil_setCode",[WINNER,codeE])
rpc("anvil_setStorageAt",[WINNER,locA,w(1)]); rpc("anvil_setStorageAt",[WINNER,locB,w(1)])
sh("fork","fund-token","ethereum",USDC,USDC_HOLDER,OWNER,str(60*U))
r=send(USDC,"0x095ea7b3"+addr_word(WINNER)+w(60*U)); assert norm(r)=="0x1"
sh("fork","fund-token","ethereum",SELL,FOLIO,WINNER,str(SELL_FUND))
sh("fork","fund-token","ethereum",BUY,FOLIO,WINNER,str(BUY_FUND))
sh("fork","fund-token","ethereum",FUNROUTER,FOLIO,WINNER,"15463863488764783939")
sh("fork","fund","ethereum",ADMIN,"1")
gsel=sh("cast","sig","grantRole(bytes32,address)")
MINTER_ROLE="0x"+"4d494e5445525f524f4c45"+"0"*42
MINTER_K="0x9f2df0fed2c77648de5860a4cc508cd0818c85b8b8a1ab4ceeef8d981c8956a6"
for tok4 in (SELL,BUY,FUNROUTER,SETTLE,WRAP):
    for role4 in (MINTER_ROLE,MINTER_K):
        r=send(tok4,gsel+role4[2:]+addr_word(WINNER),frm=ADMIN); print("grant",tok4[:10],norm(r))
hsel=sh("cast","sig","hasRole(bytes32,address)")
assert int(rpc("eth_call",[{"to":FUNROUTER,"data":hsel+MINTER_K[2:]+addr_word(WINNER)},"latest"]),16)==1
r=send(FUNROUTER,"0x40c10f19"+addr_word(WINNER)+w(5*10**18),frm=WINNER); assert norm(r)=="0x1"
sh("fork","fund-token","ethereum",SETTLE,VAULT,WINNER,"1")
sh("fork","fund-token","ethereum",USDC,USDC_HOLDER,WINNER,str(20*10**9))
sh("fork","fund-token","ethereum",USDC,USDC_HOLDER,MOD,"20000000000")
print("MOD USDC now", bal(USDC,MOD))
SPENDERS=[SWAPPER,VAULT,AGVROUTER,FUNROUTER,AGV1111,SELL,BUY]
for tok in (SELL,BUY,FUNROUTER,SETTLE):
    for sp in SPENDERS:
        r=send(tok,"0x095ea7b3"+addr_word(sp)+w(10**24),frm=WINNER); assert norm(r)=="0x1"
leg1=open(WS+"/scratch/dtf92-swap1.txt").read().strip()
legf=open(WS+"/scratch/dtf92-swap2.txt").read().strip()
SIG="fundSwapAndBid(address,uint256,address,address,uint256,uint256,uint256,uint256,bytes,bytes,bytes,uint256)"
sel=sh("cast","sig",SIG)
def fsb(min_profit,min_out,max_buy,fund,l1):
    enc=sh("cast","abi-encode","f(address,uint256,address,address,uint256,uint256,uint256,uint256,bytes,bytes,bytes,uint256)",
        FOLIO,"8",SELL,BUY,str(U),str(min_out),str(SELL_AMT),str(max_buy),fund,l1,"0x",str(min_profit))
    return sel+enc[2:]
def probe(min_profit):
    return rpc("eth_call",[{"from":OWNER,"to":WINNER,"data":fsb(min_profit,PAYFULL,PAYFULL,legf,leg1)},"latest"],soft=True)
def find(n,acc):
    if n.get("error"):
        acc.append({"from":n.get("from"),"to":n.get("to"),"fn":(n.get("input") or "")[:10],"err":n.get("error")[:140],"type":n.get("type")})
    for c in n.get("calls",[]): find(c,acc)
eA=probe(0)
print("probeA:", str(eA)[:200] if not isinstance(eA,dict) else json.dumps({k:str(v)[:120] for k,v in eA.items()}))
tr=rpc("debug_traceCall",[{"from":OWNER,"to":WINNER,"data":fsb(0,PAYFULL,PAYFULL,legf,leg1)},"latest",{"tracer":"callTracer"}],soft=True)
res=tr.get("result",tr) if isinstance(tr,dict) else {}
hits=[]; find(res,hits)
print("TRACE errors:")
for h in hits: print("  ",h)
json.dump(tr if isinstance(tr,(dict,list)) else str(tr), open(WS+"/scratch/rf-venue16-trace.json","w"))
u0,b0,s0,o0=bal(USDC,WINNER),bal(BUY,WINNER),bal(SELL,WINNER),bal(USDC,OWNER)
json.dump({"PAYFULL":str(PAYFULL),"ts0":ts0,"u0":str(u0),"b0":str(b0),"s0":str(s0),"o0":str(o0),"trace_errs":hits},open(WS+"/scratch/rf-venue16-state.json","w"),indent=1)
print("prelude done u0 b0 s0 o0:",u0,b0,s0,o0)




# --- venue28: signature enforcement test + patched funding blob probe ---
USDC="0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"
def strip_leg(leg): return leg[10:]  # drop 0x + 8-char selector? leg strings are 0x + 8-char selector
def build(head): return "0xe21fd0e9"+head
def findpos(h,s):
    i=h.find(s); assert i>=0, s+" not found"; return i
leg2=open(WS+"/scratch/dtf92-swap2.txt").read().strip()
leg1=open(WS+"/scratch/dtf92-swap1.txt").read().strip()
h2=leg2[10:]; h1=leg1[10:]
# T1: swap2 standalone from WINNER EOA to the pinned swapper (venue24 baseline: status 1, gas 1235055)
def call1(head,frm): return rpc("eth_call",[{"from":frm,"to":SWAPPER,"data":"0xe21fd0e9"+head},"latest"],soft=True)
send1=json.loads(sh("fork","send","ethereum",json.dumps({"from":WINNER,"to":SWAPPER,"data":leg2,"gas":"0x989680","value":"0x0"})))
print("T1a unpatched standalone:",send1.get("status"),"gas",send1.get("gasUsed"),send1.get("transactionHash"))
pr=findpos(h2,"418c29d29409629452")
h2f=h2[:pr]+"42"+h2[pr+2:]
e1=call1(h2f,WINNER)
print("T1b sig-flipped eth_call:",json.dumps(e1 if isinstance(e1,dict) else {"ok":"no error: "+str(e1)[:60]})[:220])
json.dump({"t1a_status":send1.get("status"),"t1a_gas":send1.get("gasUsed"),"t1b_flip_pos":pr,"t1b":str(e1)[:300]},open(WS+"/scratch/rf-venue28-t1.json","w"),indent=1)
# T2: patched swap1 funding blob (srcToken CSCO->USDC at byte 1024), settle probe with venue26 roles
USDCIN=9_057_578
MAXBUY_FILL=9_057_578_000_000_000_000
MINOUT=10**15
USDCW="a0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"
assert h1[2048:2088]=="060505527c83e8bfeb9b4ff08248b82e688800f1"
h1p=h1[:2048]+USDCW+h1[2088:]
legp="0xe21fd0e9"+h1p
def fsb3(min_profit,min_out,usdc_in,max_buy,fund,l1):
    enc=sh("cast","abi-encode","f(address,uint256,address,address,uint256,uint256,uint256,uint256,bytes,bytes,bytes,uint256)",
        FOLIO,"8",SELL,BUY,str(usdc_in),str(min_out),str(SELL_AMT),str(max_buy),fund,l1,"0x",str(min_profit))
    return sel+enc[2:]
def find3(n,acc):
    if n.get("error"):
        acc.append({"from":n.get("from"),"to":n.get("to"),"fn":(n.get("input") or "")[:10],"err":n.get("error")[:140],"type":n.get("type")})
    for c in n.get("calls",[]): find3(c,acc)
c=fsb3(0,MINOUT,USDCIN,MAXBUY_FILL,legp,leg2)
p=rpc("eth_call",[{"from":OWNER,"to":WINNER,"data":c},"latest"],soft=True)
print("T2 probe:",str(p)[:200] if isinstance(p,str) else json.dumps({k:str(v)[:130] for k,v in p.items()}))
hits3=[]
if not isinstance(p,str):
    tr3=rpc("debug_traceCall",[{"from":OWNER,"to":WINNER,"data":c},"latest",{"tracer":"callTracer"}],soft=True)
    res3=tr3.get("result",tr3) if isinstance(tr3,dict) else {}
    find3(res3,hits3)
json.dump({"probe":str(p)[:300],"trace_errs":hits3},open(WS+"/scratch/rf-venue28-t2.json","w"),indent=1)
print("T2 trace errors:",json.dumps(hits3)[:600])
ok3=isinstance(p,str)
settled=None;guard=None
if ok3:
    r=send(WINNER,c,frm=OWNER); print("SETTLE:",r.get("transactionHash"),r.get("status"),"gas",r.get("gasUsed"))
    if norm(r)=="0x1":
        settled=r.get("transactionHash")
        c2=fsb3(10**9,MINOUT,USDCIN,MAXBUY_FILL,legp,leg2)
        r2=send(WINNER,c2,frm=OWNER); print("GUARD:",r2.get("transactionHash"),r2.get("status"),"gas",r2.get("gasUsed"))
        if norm(r2)=="0x0": guard=r2.get("transactionHash")
json.dump({"t1a_status":send1.get("status"),"t2_probe":str(p)[:300],"settled":settled,"guard":guard},open(WS+"/scratch/rf-venue28-result.json","w"),indent=1)
print("venue28 done settled=",settled,"guard=",guard)
