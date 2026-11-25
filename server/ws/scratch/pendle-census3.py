import json, os, urllib.request
RELAY = os.environ["RPC_RELAY_URL"]
def rpc(method, params, lane="research"):
    req = urllib.request.Request(f"{RELAY}/ethereum?lane={lane}",
        data=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode(),
        headers={"content-type":"application/json"})
    with urllib.request.urlopen(req, timeout=120) as r: d = json.loads(r.read())
    if "error" in d: raise RuntimeError(str(d["error"])[:200])
    return d["result"]
YF="0x3e6eba46abc5ab18ed95f6667d8b2fd4020e4637"
YT_TOPIC0="0xaa79d8f17776adeaa316c5411b72e8b0057d064974fa8748f32492ecaa22ecd1"
head=int(rpc("eth_blockNumber",[]),16)
fromB=head-1000000
EXP={"2026-10-22":1792598400,"2026-10-29":1793203200,"2026-11-05":1793808000,"2026-11-12":1794412800}
maturity_pts={}
for label,e in EXP.items():
    logs=rpc("eth_getLogs",[{"address":[YF],"topics":[YT_TOPIC0,None,"0x"+hex(e)[2:].zfill(64)],"fromBlock":hex(fromB),"toBlock":hex(head)}])
    for lg in logs:
        d=lg["data"][2:]
        pt="0x"+d[0:64].lstrip("0")
        sy="0x"+lg["topics"][1][-40:]
        maturity_pts.setdefault(pt,{"mat":label,"sy":sy,"blk":int(lg["blockNumber"],16),"tx":lg["transactionHash"]})
    print(label,"PTs created:",len(logs))
print("distinct PTs maturing these weeks:",len(maturity_pts))
pts=sorted(maturity_pts)
TRANSFER="0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
ZERO32="0x"+"0"*64
def chunks(l,n):
    for i in range(0,len(l),n): yield l[i:i+n]
burns=[]; allc=[]
for ch in chunks(pts,32):
    burns+=rpc("eth_getLogs",[{"address":ch,"topics":[TRANSFER,None,ZERO32],"fromBlock":hex(head-100800),"toBlock":hex(head)}])
    allc+=rpc("eth_getLogs",[{"address":ch,"topics":[TRANSFER],"fromBlock":hex(head-100800),"toBlock":hex(head)}])
print("burns 14d:",len(burns),"all transfers 14d:",len(allc),"for",len(pts),"PTs")
# aggregate
import collections
agg=collections.Counter(); val=collections.Counter(); per={}
for lg in burns:
    pt="0x"+lg["address"][2:].zfill(40)[-40:] if len(lg["address"])==42 else "0x"+lg["address"][-40:]
    amt=int(lg["data"],16)
    agg[pt]+=1; val[pt]+=amt
    per.setdefault(pt,[]).append((int(lg["blockNumber"],16),amt,lg["transactionHash"],lg["topics"][1][-40:]))
print("burns per PT:")
for pt,c in agg.most_common():
    print(f"  {pt} mat={maturity_pts[pt]['mat']} n={c} sum={val[pt]/1e18:.2f}")
json.dump({"pts":maturity_pts,"burns":burns,"per":per,"n_all":len(allc)},open("scratch/pendle-burn-census2.json","w"))
