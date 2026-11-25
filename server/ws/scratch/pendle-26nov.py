import json, os, urllib.request
RELAY = os.environ["RPC_RELAY_URL"]
def rpc(method, params, lane="research"):
    req = urllib.request.Request(f"{RELAY}/ethereum?lane={lane}",
        data=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode(),
        headers={"content-type":"application/json"})
    for a in range(3):
        try:
            with urllib.request.urlopen(req, timeout=120) as r: d = json.loads(r.read())
            if "error" in d: raise RuntimeError(str(d["error"])[:150])
            return d["result"]
        except Exception as e:
            if a==2: raise
            print("retry:", str(e)[:150])
def call(to, data):
    return rpc("eth_call",[{"from":"0x"+"0"*40,"to":to,"data":data},"latest"])
YT0="0xaa79d8f17776adeaa316c5411b72e8b0057d064974fa8748f32492ecaa22ecd1"
TRANSFER="0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
FACTS=["0x273b4bfa3bb30fe8f32c467b5f0046834557f072","0x35a338522a435d46f77be32c70e215b813d0e3ac","0x3e6eba46abc5ab18ed95f6667d8b2fd4020e4637"]
SYM="0x95d89b41"; GSAO="0x66b9ffac"; GAD="0xe3a0d4f2"; BOF="0x70a08231"
def dec_str(h):
    h=h[2:]
    if len(h)<128: return None
    length=int(h[64:128],16)
    return bytes.fromhex(h[128:128+length*2]).decode("utf-8","replace").rstrip("\x00 ")
WAD=10**18
head=int(rpc("eth_blockNumber",[]),16)
out={"head":head}
exp="0x"+"{:0>64x}".format(1795651200)
logs=rpc("eth_getLogs",[{"address":FACTS,"topics":[YT0,None,None,exp],"fromBlock":hex(head-1000000),"toBlock":hex(head)}])
out["n_create_logs_26nov"]=len(logs)
pts=[]
for lg in logs:
    sy="0x"+"0"*(2+40-len(lg['topics'][1]))+lg['topics'][1][-40:] if False else "0x"+lg['topics'][1][-40:]
    pt="0x"+lg['topics'][2][-40:]
    blk=int(lg['blockNumber'],16)
    sym=dec_str(call(pt,SYM))
    pts.append({"sy":sy,"pt":pt,"blk":blk,"symbol":sym})
out["pts_26nov"]=pts
# for each PT named SUSDe: find pool from burn Transfers (from=pool), quote price
for p in pts:
    sym=(p["symbol"] or "")
    if "SUSDe" not in sym.replace("sUSDe","SUSDe").replace("sUSDE","SUSDe") and "sUSDe" not in sym: continue
    lg2=rpc("eth_getLogs",[{"address":[p["pt"]],"topics":[TRANSFER,None,"0x"+"0"*64],"fromBlock":hex(head-30000),"toBlock":hex(head)}])
    pools={}
    for l in lg2:
        frm="0x"+l['topics'][1][-40:]
        pools[frm]=pools.get(frm,0)+int(l['data'],16)
    p["burns_30k"]=len(lg2); p["pool_candidates"]={k:round(v/1e18,1) for k,v in sorted(pools.items(),key=lambda kv:-kv[1])}
    for pool in list(pools)[:1]:
        try:
            ad=call(pool,GAD)[2:]
            sy="0x"+ad[24:64][-40:]; pt="0x"+ad[88:128][-40:]
            quote=call(pool,GSAO+"0"*24+pt[2:]+"0"*32+"{:0>32x}".format(WAD))
            srb=int(call(sy,"0x70a08231"+pool[2:].rjust(64,"0")),16)
            p["pool"]={"addr":pool,"sy":sy,"pt_matches":pt==p["pt"],"pt_to_sy_quote":int(quote,16)/1e18,"sy_reserve":srb/1e18}
        except Exception as e:
            p["pool"]={"addr":pool,"error":str(e)[:120]}
json.dump(out,open("scratch/pendle-26nov.json","w"),indent=1)
print(json.dumps(out,indent=1))
