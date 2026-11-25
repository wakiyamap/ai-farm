import json, urllib.request, time
HDRS={"content-type":"application/json","User-Agent":"Mozilla/5.0"}
URL="https://subnets.avax.network/dexalot/mainnet/rpc"
MAN="0x7AAC6aa9345a436D459316D8Dd1275b78DBbA3F3"
def raw(vid):
    sel="0xc0b579c0"; data=sel+"%064x"%vid
    body={"jsonrpc":"2.0","id":1,"method":"eth_call","params":[{"to":MAN,"data":data},"latest"]}
    req=urllib.request.Request(URL,data=json.dumps(body).encode(),headers=HDRS)
    return json.loads(urllib.request.urlopen(req,timeout=20).read()).get("result")
def get(d,i):
    s=d[i:i+64]
    if len(s)!=64: return None
    return int(s,16)
def addr(d,i):
    s=d[i+40:i+64]
    return "0x"+s if len(s)==24 else None
def valid(d):
    if len(d)%64: return False
    if get(d,0)!=32: return False
    t=32
    no=get(d,t); 
    if no is None or no<32 or no>=len(d): return False
    nl=get(d,no)
    if nl is None or nl>100: return False
    st=get(d,t+96)
    if st is None or st>255: return False
    for off in (t+32,t+64,t+128,t+160,t+192):
        s=d[off+40:off+64]
        if len(s)!=24 or not s.startswith("0"*22): return False
    co=get(d,t+224); to_=get(d,t+256)
    if co is None or to_ is None or co>=len(d) or to_>=len(d): return False
    cl=get(d,co); tl=get(d,to_)
    if cl is None or tl is None or cl>20 or tl>20: return False
    return True
def getv(vid, tries=12):
    for k in range(tries):
        h=raw(vid)
        if not h or len(h)<100: time.sleep(0.6); continue
        s=h[2:]
        if len(s)%64: s=s.zfill(((len(s)+63)//64)*64)
        if not valid(s): time.sleep(0.6); continue
        d=s; t=32
        no=get(d,t); nl=get(d,no)
        name=bytes.fromhex(d[no+64:no+64+nl*2]).decode(errors="replace") if nl else ""
        cl=get(d,get(d,t+224)); tl=get(d,get(d,t+256))
        row=dict(id=vid,name=name,status=get(d,t+96),proposer=addr(d,t+32),
            omniTrader=addr(d,t+64),executor=addr(d,t+128),
            shareToken=addr(d,t+160),dexalotRFQ=addr(d,t+192),
            chainIds=[get(d,get(d,t+224)+64+64*i) for i in range(cl)],
            tokens=[get(d,get(d,t+256)+64+64*i) for i in range(tl)])
        return row
    return None
out={}
for vid in range(0,12):
    row=getv(vid)
    if not row: print(vid,"GIVEUP"); continue
    out[vid]=row
    print(vid,repr(row["name"]),"st",row["status"],"exec",row["executor"],"rfq",row["dexalotRFQ"],"chains",row["chainIds"],"tokens",row["tokens"])
json.dump(out,open("scratch/omnivault-details-f08ee7c2.json","w"),indent=1)
