import json, os, urllib.request, datetime
RELAY = os.environ["RPC_RELAY_URL"]
def rpc(method, params, lane="research"):
    req = urllib.request.Request(f"{RELAY}/ethereum?lane={lane}",
        data=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode(),
        headers={"content-type":"application/json"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=90) as r: d = json.loads(r.read())
            if "error" in d: raise RuntimeError(str(d["error"])[:150])
            return d["result"]
        except Exception as e:
            if attempt == 2: raise
            print("retry:", str(e)[:80])
def call(to, data):
    return rpc("eth_call",[{"from":"0x"+"0"*40,"to":to,"data":data},"latest"])
def dec_str(h):
    h=h[2:]
    if len(h) < 128: return None
    length=int(h[64:128],16)
    raw=bytes.fromhex(h[128:128+length*2])
    return raw.decode("utf-8","replace").rstrip("\x00 ")
SYM="0x95d89b41"
GAD="0xe3a0d4f2"   # getAssetData()
GSAO="0x66b9ffac"  # getSwapAmountOut(address,uint128)
BOF="0x70a08231"   # balanceOf(address)
WAD=10**18

# ledger creation events (already ingested, cursor verified at head)
new_cohorts = [
 # batch Nov 5 (block 26326597)
 ("0xca7a1774d50c2bf3ebdeb205bf72390743752231","0xcb3760b19538db4e5506debf8f73c963824e997d",1803772800,"2027-01-01"),
 ("0x711fbd23db52f49993d5c460946bd3cba2424ff3","0x49f53e69ce7e2a4b00de951fc9395855ee0957be",1811721600,"2027-04-01"),
 ("0x6689ebb7b8b0da99befdf6974310d733f6166e40","0xd65925e1fc72b16b8a5e8c8336c2c82ba9dd6bb6",1819670400,"2027-07-01"),
 ("0xf3135b0ba174b502ac22a6a9cfe996542a7e353f","0x1cae1e0a328485e100be74866c829948f170d143",1827532800,"2027-10-01"),
 # batch Nov 7 (blocks 26354709-21)
 ("0x31853542da976400fb66278be7a09636aad332fc","0x65bc0a0cf38ecdfc95e553de01af01a56da225ce",1803772800,"2027-01-01"),
 ("0xa57854210b569aabf55f8f99ad16705053e563b8","0x2757eea99c54dcb9e319ae00f08fe841e4574450",1811721600,"2027-04-01"),
 ("0xc994861c0041d88addf99fd136fe94fdd9b634bf","0x9327c9743d06efce3f784049f1aeed3d63a05be6",1819670400,"2027-07-01"),
 ("0x1593d2b64365bed60caf54ecb7448171214e33c1","0x247934a535e4a37b95c13feb7efef778e39dc7e5",1827532800,"2027-10-01"),
]
out={"head":int(rpc("eth_blockNumber",[]),16)}
names={}
for sy,pt,mat,lab in new_cohorts:
    try:
        names[pt.lower()]={"symbol":dec_str(call(pt.lower(),SYM)),"mat":lab,"sy":sy}
    except Exception as e:
        names[pt.lower()]={"symbol":"REVERT "+str(e)[:60],"mat":lab,"sy":sy}
out["new_cohort_names"]=names

# the two 26NOV2026-expiry PTs from the earlier cycle census (scratch/pendle-cyc-pts.json)
for pt in ["0x5b2922c27f9f4f9ba36ed6b745dee97fa2a31c7f","0xe2dbd6bafcd6b1da90483108f0f437addf7bd885"]:
    try:
        out.setdefault("pt26nov",{})[pt]={"symbol":dec_str(call(pt,SYM))}
    except Exception as e:
        out.setdefault("pt26nov",{})[pt]={"symbol":"REVERT "+str(e)[:60]}

POOL="0xa3b85dd45e46982956c84b8b0223460e520d7401"   # pool that burned the discounted PT->SY swaps (scratch/pendle-burn-txs.json)
PT_SUSDE="0x6ab3353296c44c305ba2b9c17743a26d2f6359e"  # placeholder, overwritten below from getAssetData
try:
    ad=call(POOL,GAD)[2:]
    sy="0x"+ad[24:64][-40:]; pt="0x"+ad[88:128][-40:]; lp=int(ad[192:256],16)
    out["pool_assets"]={"sy":sy,"pt":pt,"lp_supply_lp":lp/1e18}
    out["pool_pt_symbol"]=dec_str(call(pt,SYM))
    srb=int(call(sy,"0x70a08231"+POOL[2:].rjust(64,"0")),16)   # SY.balanceOf(pool)
    prb=int(call(pt,"0x70a08231"+POOL[2:].rjust(64,"0")),16)
    out["sy_reserve"]=srb/1e18; out["pt_reserve"]=prb/1e18
    # marginal PT->SY price: getSwapAmountOut(pt token, sell 1 PT)
    q=call(POOL,GSAO+"0"*24+pt[2:]+"0"*32+"{:0>32x}".format(WAD))
    out["pt_to_sy_quote"]=int(q,16)/1e18
except Exception as e:
    out["pool_error"]=str(e)[:200]
# positive control: known-active pool still quotes (the quote above) AND symbol decode works on a known PT name from earlier census
try:
    known_pt="0xf1a905616171e1472b0c71eaa9caf7f224f04916"  # "ETF (Ondo Tokenized) 10DEC2026" per scratch/pendle-cyc-pts.json
    out["control_symbol"]=dec_str(call(known_pt,SYM))
except Exception as e:
    out["control_symbol"]="REVERT "+str(e)[:60]
json.dump(out,open("scratch/pendle-gate.json","w"),indent=1)
print(json.dumps(out,indent=1))
