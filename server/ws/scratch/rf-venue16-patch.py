import json, urllib.request, subprocess, os
WS="/srv/farm/ws"
ENV=dict(os.environ, PATH="/opt/farm/bin:/opt/foundry/bin:"+os.environ.get("PATH",""))
def sh(*c):
    r=subprocess.run(c, capture_output=True, text=True, env=ENV)
    if r.returncode!=0: raise SystemExit("FAILED %s: %s%s"%(c[:3],r.stdout[-200:],r.stderr[-200:]))
    return r.stdout.strip()
def rpc(method, params, soft=False):
    body=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    req=urllib.request.Request("http://127.0.0.1:9003",data=body,headers={"content-type":"application/json"})
    out=json.loads(urllib.request.urlopen(req,timeout=180).read())
    if "error" in out:
        if soft: return out["error"]
        raise SystemExit("RPC %s: %s"%(method,out["error"]))
    return out["result"]
def keccak(hb): return sh("cast","keccak",hb)[2:]
def norm(res):
    s=str(res.get("status")); return "0x1" if s in ("0x1","1") else "0x0"
def send(to,calldata,frm=None):
    return json.loads(sh("fork","send","ethereum",json.dumps({"from":frm or OWNER,"to":to,"data":calldata,"gas":"0x989680","value":"0x0"})))
IMPL="0xf036cfa5e0e796195cfb8cf7f1a89b4aaca6883b"
MOD="0xa88cd6b934c64ea830b78967b2f8a0de91577edc"
WINNER="0xd98d34008d1bbb29013592c637f8e9fca4179fa0"
OWNER="0x000000000000000000000000000000000000f007"
RESET=26306742
REQ=1794573000; OFF=1794572444
ts0=int(rpc("eth_getBlockByNumber",[hex(RESET),False])["timestamp"],16)
STORED=1793377428  # measured offered side of the fee revert at this fetched state (= ts0+37)
print("ts0",ts0,"stored",STORED,STORED-ts0)
tr=json.load(open(WS+"/scratch/rf-venue16-trace.json"))
res=tr["result"] if "result" in tr else tr
frames=[]
def walk(n):
    frames.append(n)
    for c in n.get("calls",[]): walk(c)
walk(res)
fee=[f for f in frames if f.get("to")==IMPL and (f.get("input") or "").startswith("0xf05bb6c4")][-1]
data=fee["input"]
b=bytes.fromhex(data[2:])
words=[b[4+32*i:4+32*(i+1)].hex() for i in range((len(b)-4)//32)]
keys=set()
for w in words:
    iv=int(w,16)
    if iv==0: continue
    keys.add(w)
    if iv<2**160: keys.add(w[-40:]+"0"*24)
    if iv<2**64: keys.add("%064x"%iv)
keys.add("%064x"%8); keys.add("%064x"%RESET)
keys.add(keccak("0x"+open(WS+"/scratch/dtf92-swap1.txt").read().strip()[2:]))
keys.add(keccak("0x"+open(WS+"/scratch/dtf92-swap2.txt").read().strip()[2:]))
bases=[2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20]
hits=[]; cands=[]
for k in keys:
    for base in bases:
        loc="0x"+keccak("0x"+k+"%064x"%base)
        cands.append((k,base,loc))
print("cands",len(cands))
for k,base,loc in cands:
    v=int(rpc("eth_getStorageAt",[MOD,loc,"latest"]),16)
    if v==STORED: hits.append((k,base,loc))
    elif abs(v-STORED)<=300: hits.append((k,base,loc))
print("hits:",hits)
def fee_call():
    return rpc("eth_call",[{"to":IMPL,"data":data},"latest"],soft=True)
def pair(rr):
    d=str((rr or {}).get("data") or "")
    if len(d)>=138 and d[2:10]=="3e9e7bf1": return (int(d[10:74],16),int(d[74:138],16))
    return None
if not hits:
    # fallback patch-all
    for k,base,loc in cands:
        v=int(rpc("eth_getStorageAt",[MOD,loc,"latest"]),16)
        if v==0: rpc("anvil_setStorageAt",[MOD,loc,"0x"+"%064x"%REQ])
    rr=fee_call(); print("patch-all fee:", str(rr)[:100], pair(rr))
else:
    for k,base,loc in hits:
        rpc("anvil_setStorageAt",[MOD,loc,"0x"+"%064x"%REQ])
    rr=fee_call(); p=pair(rr)
    print("patched fee:", str(rr)[:100], p)
    assert p is None, "fee still reverting"
# settlement control + success at ts0+3600
state=json.load(open(WS+"/scratch/rf-venue16-state.json"))
PAYFULL=int(state["PAYFULL"]); u0=int(state["u0"]); o0=int(state["o0"])
FOLIO="0x2cf4dafc17e163abd6770e1794e1ad10deb7d32e"; SELL="0x060505527c83e8bfeb9b4ff08248b82e688800f1"; BUY="0xf404e5f887dbd5508e16a1198fcdd5de1a4296b8"
USDC="0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"; U=9_057_578; SELL_AMT=57582275034043643305
leg1=open(WS+"/scratch/dtf92-swap1.txt").read().strip(); legf=open(WS+"/scratch/dtf92-swap2.txt").read().strip()
sel=sh("cast","sig","fundSwapAndBid(address,uint256,address,address,uint256,uint256,uint256,uint256,bytes,bytes,bytes,uint256)")
def fsb(min_profit,min_out,max_buy):
    enc=sh("cast","abi-encode","f(address,uint256,address,address,uint256,uint256,uint256,uint256,bytes,bytes,bytes,uint256)",
        FOLIO,"8",SELL,BUY,str(U),str(min_out),str(SELL_AMT),str(max_buy),legf,leg1,"0x",str(min_profit))
    return sel+enc[2:]
def bal(t,who): return int(rpc("eth_call",[{"to":t,"data":"0x70a08231"+who[2:].lower().rjust(64,"0")},"latest"]),16)
tsC=ts0+3600
rpc("anvil_setNextBlockTimestamp",["0x"+"%x"%tsC])
r=send(WINNER,fsb(10**12,PAYFULL,PAYFULL))
print("control:",r.get("transactionHash"),norm(r))
assert norm(r)=="0x0"
rpc("anvil_setNextBlockTimestamp",["0x"+"%x"%(tsC+12)])
r=send(WINNER,fsb(0,PAYFULL,PAYFULL))
print("success:",r.get("transactionHash"),norm(r),"gas",int(r.get("gasUsed"),16))
du=bal(USDC,WINNER)-u0; od=bal(USDC,OWNER)-o0
print("USDC delta WINNER:",du,"OWNER:",od)
json.dump({"ts0":ts0,"hits":[str(h) for h in hits],"control":r.get("transactionHash"),"success_gas":int(r.get("gasUsed"),16),"owner_delta":od},open(WS+"/scratch/rf-venue16-result.json","w"),indent=1)
