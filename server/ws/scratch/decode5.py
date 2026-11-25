import json, urllib.request, time
HDRS={"content-type":"application/json","User-Agent":"Mozilla/5.0"}
URL="https://subnets.avax.network/dexalot/mainnet/rpc"
MAN="0x7AAC6aa9345a436D459316D8Dd1275b78DBbA3F3"
def raw(vid, tries=12):
    data="0xc0b579c0"+"%064x"%vid
    body={"jsonrpc":"2.0","id":1,"method":"eth_call","params":[{"to":MAN,"data":data},"latest"]}
    for k in range(tries):
        try:
            req=urllib.request.Request(URL,data=json.dumps(body).encode(),headers=HDRS)
            r=json.loads(urllib.request.urlopen(req,timeout=25).read())
        except Exception: time.sleep(1); continue
        res=r.get("result")
        if isinstance(res,str) and len(res)>=100 and (len(res)-2)%64==0 and len(res)%2==0:
            return res[2:]
        time.sleep(1)
    return None
def w(d,hexpos):
    s=d[hexpos:hexpos+64]
    return int(s,16) if len(s)==64 else None
def getv(vid):
    d=raw(vid)
    if not d: return None
    t=w(d,0)*2            # tuple start (hex chars)
    no=w(d,t)*2; nl=w(d,no)
    name=bytes.fromhex(d[no+64:no+64+nl*2]).decode(errors="replace") if nl else ""
    co=w(d,t+448)*2; cl=w(d,co); to_=w(d,t+512)*2; tl=w(d,to_)
    row=dict(id=vid,name=name,status=w(d,t+192),
        proposer="0x"+d[t+64+40:t+64+64], omniTrader="0x"+d[t+128+40:t+128+64],
        executor="0x"+d[t+256+40:t+256+64], shareToken="0x"+d[t+320+40:t+320+64],
        dexalotRFQ="0x"+d[t+384+40:t+384+64],
        chainIds=[w(d,co+64+64*i) for i in range(cl)],
        tokens=[w(d,to_+64+64*i) for i in range(tl)])
    return row
out={}
for vid in range(0,12):
    row=getv(vid)
    if not row: print(vid,"GIVEUP"); continue
    out[vid]=row
    print(vid,repr(row["name"]),"st",row["status"],"exec",row["executor"],"rfq",row["dexalotRFQ"],"chains",row["chainIds"],"tokens",row["tokens"])
json.dump(out,open("scratch/omnivault-details-f08ee7c2.json","w"),indent=1)
