import json, urllib.request, time
HDRS = {"content-type":"application/json","User-Agent":"Mozilla/5.0"}
URL="https://subnets.avax.network/dexalot/mainnet/rpc"

def call(vid, tries=8):
    sel="0xc0b579c0"; data=sel+"%064x"%vid
    body={"jsonrpc":"2.0","id":1,"method":"eth_call",
         "params":[{"to":"0x7AAC6aa9345a436D459316D8Dd1275b78DBbA3F3","data":data},"latest"]}
    for k in range(tries):
        try:
            req=urllib.request.Request(URL,data=json.dumps(body).encode(),headers=HDRS)
            r=json.loads(urllib.request.urlopen(req,timeout=20).read())
            res=r.get("result")
        except Exception:
            time.sleep(1); continue
        if isinstance(res,str) and len(res)>=100 and len(res)%2==0:
            s=res[2:]
            if len(s)%64!=0:
                s=s.zfill(((len(s)+63)//64)*64)
            if s[:64].lstrip("0") in ("","20","40"):  # plausible top offset
                return "0x"+s
        time.sleep(1)
    return None

def get(d,i): return int(d[i:i+64],16)

out={}
for vid in range(0,12):
    h=call(vid)
    if not h: print(vid,"NO-DATA"); continue
    d=h[2:]
    t=get(d,0)
    name_off=get(d,t); name_len=get(d,name_off)
    name=bytes.fromhex(d[name_off+64:name_off+64+name_len*2]).decode(errors="replace") if name_len else ""
    row=dict(id=vid,name=name,status=get(d,t+96),proposer="0x"+d[t+32+40:t+32+64],
        omniTrader="0x"+d[t+64+40:t+64+64],executor="0x"+d[t+128+40:t+128+64],
        shareToken="0x"+d[t+160+40:t+160+64],dexalotRFQ="0x"+d[t+192+40:t+192+64],
        chainIds=[get(d,get(d,t+224)+64+64*i) for i in range(get(d,get(d,t+224)))],
        tokens=[get(d,get(d,t+256)+64+64*i) for i in range(get(d,get(d,t+256)))])
    out[vid]=row
    print(vid,repr(row["name"]),"st",row["status"],"exec",row["executor"],"rfq",row["dexalotRFQ"],"chains",row["chainIds"],"tokens",row["tokens"])
json.dump(out,open("scratch/omnivault-details-f08ee7c2.json","w"),indent=1)
