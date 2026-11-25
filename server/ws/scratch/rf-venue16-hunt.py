import json, urllib.request, subprocess, os, re
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
IMPL="0xf036cfa5e0e796195cfb8cf7f1a89b4aaca6883b"
MOD="0xa88cd6b934c64ea830b78967b2f8a0de91577edc"
REQ=1794573000; OFF=1794572444
tr=json.load(open(WS+"/scratch/rf-venue16-trace.json"))
res=tr.get("result",tr)
frames=[]
def walk(n):
    frames.append(n)
    for c in n.get("calls",[]): walk(c)
walk(res)
fee=[f for f in frames if f.get("to")==IMPL and (f.get("input") or "").startswith("0xf05bb6c4")][-1]
data=fee["input"]
# fee call directly on impl and on MOD proxy
def fee_call(to, d):
    return rpc("eth_call",[{"to":to,"data":d},"latest"],soft=True)
r0=fee_call(IMPL,data)
print("impl fee revert:", str(r0)[:180])
r1=fee_call(MOD,data)
print("MOD fee revert:", str(r1)[:180])
def pair(res_):
    d=str((res_ or {}).get("data") or "")
    if len(d)>=138 and d[2:10]=="3e9e7bf1": return (int(d[10:74],16), int(d[74:138],16))
    return None
p0=pair(r0) or pair(r1)
print("fee revert pair:", p0)
assert p0 and p0[1]==REQ, "unexpected pair"
# word extraction
b=bytes.fromhex(data[2:])
words=[b[4+32*i:4+32*(i+1)].hex() for i in range((len(b)-4)//32)]
keys=set()
for i,w in enumerate(words,1):
    iv=int(w,16)
    if iv==0: continue
    keys.add(w)                      # word as-is
    if iv<2**160: keys.add(w[-40:]+"0"*24)  # address left-padded
    if iv<2**64: keys.add(hex(iv)[2:].zfill(64))
# extra key candidates
addr_candidates={
 "hash2":words[1], "addr3":words[2], "clone4":words[3], "expiry5":words[4],
 "small6":words[5], "nonce21":words[20],
}
for k in addr_candidates.values(): keys.add(k[-64:])
keys.add("%064x"%8)  # auction id 8
h_blob1=keccak("0x"+open(WS+"/scratch/dtf92-swap1.txt").read().strip()[2:])
h_blob2=keccak("0x"+open(WS+"/scratch/dtf92-swap2.txt").read().strip()[2:])
keys.add(h_blob1); keys.add(h_blob2)
bases=[2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20]
cands=[]
for k in keys:
    for base in bases:
        loc="0x"+keccak("0x"+k+"%064x"%base)
        cands.append((k,base,loc))
print("candidates:", len(cands))
# read current values first (cheap, mostly cached) then patch all to REQ-1? use REQ+1? use value >OFF: patch to OFF+1? We'll patch to REQ (same) then look for pair change...
# patch every candidate to REQ+7 so required-side changes are detectable
cur={}
for (k,base,loc) in cands[:len(cands)]:
    cur[loc]=int(rpc("eth_getStorageAt",[MOD,loc,"latest"]),16)
changed=set()
for (k,base,loc) in cands:
    v=cur[loc]
    if v in (REQ, REQ+7):
        changed.add((k,base,loc,v))
print("already REQ:", changed)
for (k,base,loc) in cands:
    if cur[loc]!=REQ: rpc("anvil_setStorageAt",[MOD,loc,"0x"+"%064x"%(REQ+7)])
rA=fee_call(IMPL,data); print("after-patch-all revert:", str(rA)[:160], pair(rA))
# restore: candidates that were zero: set back 0 individually in second pass after finding the slot
# find which single candidate matters: set all others back? simpler: bisect: set each REQ+7 back to 0 one by one until pair returns
import itertools
# binary search: split list, zero half, test
def reverted_pair():
    rr=fee_call(IMPL,data); return pair(rr)
cand_list=[c for c in cands if cur[c[2]]!=REQ]
# first confirm full patch changed pair:
pA=pair(rA)
if pA is None:
    print("pair gone entirely - check msg:", str(rA)[:120])
lo, hi = 0, len(cand_list)
# iterative bisection: keep patch for [lo,hi), zero the rest
def set_range(active_set):
    for c in cand_list:
        if c in active_set: rpc("anvil_setStorageAt",[MOD,c[2],"0x"+"%064x"%(REQ+7)])
        else: rpc("anvil_setStorageAt",[MOD,c[2],"0x"+"%064x"%0])
    return reverted_pair()
# start: all active
pA2=set_range(set(cand_list)); print("all active pair:", pA2)
# bisect
while len(cand_list)>1:
    mid=len(cand_list)//2
    act=set(cand_list[:mid])
    p=set_range(act)
    print("half active(%d):"%len(act), p)
    if p and p[1]!=REQ: cand_list=list(act)   # culprit in first half
    else: cand_list=[c for c in cand_list if c not in act]
print("culprit candidate:", cand_list[0], "cur value", cur[cand_list[0][2]])
json.dump({"candidate":cand_list[0],"cur":cur[cand_list[0][2]]}, open(WS+"/scratch/rf-venue16-slot.json","w"),indent=1)
