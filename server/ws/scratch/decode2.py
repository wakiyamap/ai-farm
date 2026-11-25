import json, urllib.request, time
exec(open("scratch/decode_omnivault_f08ee7c2.py").read().split("out={}")[0])
def get2(d,i):
    s=d[i:i+64]
    if len(s)!=64: raise ValueError(f"slice short at {i} dlen {len(d)}")
    return int(s,16)
def getv(vid, tries=10):
    for k in range(tries):
        h=call(vid)
        if not h: time.sleep(1); continue
        d=h[2:]
        t=get2(d,0)
        if t not in (32,64,96): print(vid,"retry bad word0",repr(d[0:64])); time.sleep(0.5); continue
        name_off=get2(d,t)
        if name_off<32 or name_off>=len(d): print(vid,"retry bad name_off",name_off, "len", len(d), "w1", repr(d[t:t+64])); time.sleep(0.5); continue
        name_len=get2(d,name_off)
        if name_len>100: print(vid,"retry bad name_len",name_len); time.sleep(0.5); continue
        name=bytes.fromhex(d[name_off+64:name_off+64+name_len*2]).decode(errors="replace") if name_len else ""
        row=dict(id=vid,name=name,status=get2(d,t+96),proposer="0x"+d[t+32+40:t+32+64],
            omniTrader="0x"+d[t+64+40:t+64+64],executor="0x"+d[t+128+40:t+128+64],
            shareToken="0x"+d[t+160+40:t+160+64],dexalotRFQ="0x"+d[t+192+40:t+192+64],
            chainIds=[get2(d,get2(d,t+224)+64+64*i) for i in range(get2(d,get2(d,t+224)))],
            tokens=[get2(d,get2(d,t+256)+64+64*i) for i in range(get2(d,get2(d,t+256)))])
        return row
    return None
out={}
for vid in range(0,12):
    row=getv(vid)
    if not row: print(vid,"GIVEUP"); continue
    out[vid]=row
    print(vid,repr(row["name"]),"st",row["status"],"exec",row["executor"],"rfq",row["dexalotRFQ"],"chains",row["chainIds"],"tokens",row["tokens"])
json.dump(out,open("scratch/omnivault-details-f08ee7c2.json","w"),indent=1)
