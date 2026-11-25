import json
def w(d,p):
    s=d[p:p+64]
    return int(s,16) if len(s)==64 else None
def arr(d, ptr_bytes):
    lp = ptr_bytes*2 + 64   # length word (this encoder points 32 bytes before it)
    ln = w(d,lp)
    return [w(d,lp+64+64*i) for i in range(ln)] if ln is not None and ln<=20 else None
def a(d,p):  # 40-hex-char address = last 40 chars of word at p
    return "0x"+d[p+24:p+64]
out={}
for vid in range(0,12):
    r=json.load(open(f"scratch/vd/v{vid}.json"))
    res=r.get("result")
    if not res: print(vid,"ERR",r.get("error")); continue
    d=res[2:]
    t=w(d,0)*2
    no=w(d,t)*2; nl=w(d,no+64)
    name=bytes.fromhex(d[no+128:no+128+nl*2]).decode(errors="replace") if nl else ""
    row=dict(id=vid,name=name,status=w(d,t+192),
        proposer=a(d,t+64), omniTrader=a(d,t+128),
        executor=a(d,t+256), shareToken=a(d,t+320), dexalotRFQ=a(d,t+384),
        chainIds=arr(d,w(d,t+448)), tokens=arr(d,w(d,t+512)))
    out[vid]=row
    print(vid,repr(name),"st",row["status"],"exec",row["executor"],"rfq",row["dexalotRFQ"],"chains",row["chainIds"],"tokens",row["tokens"])
json.dump(out,open("scratch/omnivault-details-f08ee7c2.json","w"),indent=1)
