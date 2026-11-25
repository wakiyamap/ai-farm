import json
def w(d,p):
    s=d[p:p+64]
    return int(s,16) if len(s)==64 else None
def arr(d, ptr_bytes):
    # this encoder points 32 bytes before the length word
    lp = ptr_bytes*2 + 64
    ln = w(d,lp)
    return [w(d,lp+64+64*i) for i in range(ln)] if ln is not None and ln<=20 else None
out={}
for vid in range(0,12):
    r=json.load(open(f"scratch/vd/v{vid}.json"))
    res=r.get("result")
    if not res: print(vid,"ERR",r.get("error")); continue
    d=res[2:]
    t=w(d,0)*2            # tuple start hex pos
    no=w(d,t)*2; nl=w(d,no+64)
    name=bytes.fromhex(d[no+128:no+128+nl*2]).decode(errors="replace") if nl else ""
    cl=w(d,w(d,t+448)*2+64); tl=w(d,w(d,t+512)*2+64)
    row=dict(id=vid,name=name,status=w(d,t+192),
        proposer="0x"+d[t+64+40:t+64+64], omniTrader="0x"+d[t+128+40:t+128+64],
        executor="0x"+d[t+256+40:t+256+64], shareToken="0x"+d[t+320+40:t+320+64],
        dexalotRFQ="0x"+d[t+384+40:t+384+64],
        chainIds=arr(d,w(d,t+448)), tokens=arr(d,w(d,t+512)))
    out[vid]=row
    print(vid,repr(name),"st",row["status"],"exec",row["executor"],"rfq",row["dexalotRFQ"],"chains",row["chainIds"],"tokens",row["tokens"])
json.dump(out,open("scratch/omnivault-details-f08ee7c2.json","w"),indent=1)
