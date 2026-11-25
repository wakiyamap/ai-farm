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
def w(d,hexpos):  # hexpos in hex chars
    s=d[hexpos:hexpos+64]
    return int(s,16) if len(s)==64 else None
def getv(vid):
    d=raw(vid)
    if not d: return None
    t=w(d,0)*2
    no=w(d,t)*2; nl=w(d,no)
    name=bytes.fromhex(d[no+64:no+64+nl*2]).decode(errors="replace") if nl else ""
    cl=w(d,w(d,t+224)*2); tl=w(d,w(d,t+256)*2)
    row=dict(id=vid,name=name,status=w(d,t+96),
        proposer="0x"+d[t+32+80:t+32+128], omniTrader="0x"+d[t+64+80:t+64+128],
        executor="0x"+d[t+128+80:t+128+128], shareToken="0x"+d[t+160+80:t+160+128],
        dexalotRFQ="0x"+d[t+192+80:t+192+128],
        chainIds=[w(d,w(d,t+224)*2+64+64*i) for i in range(cl)],
        tokens=[w(d,w(d,t+256)*2+64+64*i) for i in range(tl)])
    return row
out={}
for vid in range(0,12):
    row=getv(vid)
    if not row: print(vid,"GIVEUP"); continue
    out[vid]=row
    print(vid,repr(row["name"]),"st",row["status"],"exec",row["executor"],"rfq",row["dexalotRFQ"],"chains",row["chainIds"],"tokens",row["tokens"])
json.dump(out,open("scratch/omnivault-details-f08ee7c2.json","w"),indent=1)
