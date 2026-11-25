import json, urllib.request, time, os
URL=os.environ["RPC_RELAY_URL"]; LANE="research"
SEL="0x5ec88c79"; COMPT="0xfbb21d0380bee3312b33c4353c8936a0f13ef26c"
def call(borrower, tag, tries=6):
    data="0x5ec88c79"+borrower[2:].rjust(64,"0")
    body=json.dumps({"jsonrpc":"2.0","id":1,"method":"eth_call","params":[{"from":"0x0000000000000000000000000000000000000001","to":COMPT,"data":data},hex(tag)]}).encode()
    req=urllib.request.Request(f"{URL}/base?lane={LANE}",data=body,headers={"content-type":"application/json"})
    for t in range(tries):
        try:
            r=json.loads(urllib.request.urlopen(req,timeout=30).read())
            if "error" in r: raise RuntimeError(r["error"])
            w=r["result"][2:]
            liq=int(w[0:64],16); short=int(w[64:128],16)
            return liq,short
        except Exception as e:
            time.sleep(2)
    raise RuntimeError("relay fail")
cap=json.loads(open("scratch/mw-rerun-caps.json").read())
out={}
for c in cap:
    B=c["block"]; bor=c["borrower"]
    # control: liquidatable pre-capture (tag B = end of B-1)
    ctl=call(bor,B)
    res={"ctl_shortfall":ctl[1],"ctl_liquidatable":ctl[1]>0,"window_blocks":0}
    if ctl[1]>0:
        # descending ladder, stop at first liquidatable
        for W in (65536,16384,4096,1024,256,64,16,4,1):
            try:
                p=call(bor,B-W)
            except RuntimeError:
                p=(0,0)  # too-old tag maybe
            if p[1]>0:
                res["window_blocks"]=W; break
    out[f"{B}_{bor[:8]}"]=res
    print(B, bor[:10], res, flush=True)
json.dump(out,open("scratch/mw-rerun-window.json","w"),indent=1)
