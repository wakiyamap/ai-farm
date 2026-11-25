import json, os, urllib.request, datetime
RELAY = os.environ["RPC_RELAY_URL"]
REQ=[]
def rpc(method, params, lane="research"):
    global REQ
    REQ.append((method,len(str(params))))
    req = urllib.request.Request(f"{RELAY}/ethereum?lane={lane}",
        data=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode(),
        headers={"content-type":"application/json"})
    with urllib.request.urlopen(req, timeout=120) as r: d = json.loads(r.read())
    if "error" in d: raise RuntimeError(str(d["error"])[:200])
    return d["result"]

summary=json.load(open("scratch/pendle-yf-summary.json"))
SY=summary["sy"]
YF="0x3e6eba46abc5ab18ed95f6667d8b2fd4020e4637"
GETPT="0x"+(__import__("subprocess").run(["cast","keccak","getPT(address,uint256)"],capture_output=True,env={**os.environ,"PATH":"/opt/foundry/bin"}).stdout.decode().strip()[2:10])
EXP={"2026-10-22":1792598400,"2026-10-29":1793203200,"2026-11-05":1793808000,"2026-11-12":1794412800}
maturity_pts={}  # pt -> maturity str
for s in SY:
    for label,e in EXP.items():
        data=GETPT+ s[2:].zfill(64) + hex(e)[2:].zfill(64)
        try:
            r=rpc("eth_call",[{"from":"0x0000000000000000000000000000000000000000","to":YF,"data":"0x"+data},"latest"])
            a="0x"+r[-40:]
            if a!="0x"+"0"*40:
                maturity_pts[a]=label
        except RuntimeError:
            pass
print("hits by maturity:")
by={}
for p,m in maturity_pts.items(): by.setdefault(m,[]).append(p)
for m,v in sorted(by.items()): print(" ",m,len(v))
# cohort already-matured PTs from market-creation census
cohort=["0x1c610c120035bf9d1a0b7752c3c7bf9febff7cae","0x17c47b0cedec9b41e639f5ec1a053e9135db2a6d","0xe3cdf5b8d7aedfc9f768dbdcc334146fae989188","0x79b6d7e48d18ad20f229d2192a0ac30b7b365d8a","0x12ba8d7e25a581d4534f5ada63105e016ae4d4bb"]
for c in cohort: maturity_pts.setdefault(c,"cohort2026")
pts=sorted(maturity_pts)
print("total census PTs:",len(pts))

head=int(rpc("eth_blockNumber",[]),16)
fromB=head-100800
TRANSFER="0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
ZERO32="0x"+"0"*64
def chunks(l,n):
    for i in range(0,len(l),n): yield l[i:i+n]
burns=[]; allc=[]
for ch in chunks(pts,32):
    burns+=rpc("eth_getLogs",[{"address":ch,"topics":[TRANSFER,None,ZERO32],"fromBlock":hex(fromB),"toBlock":hex(head)}])
    allc+=rpc("eth_getLogs",[{"address":ch,"topics":[TRANSFER],"fromBlock":hex(fromB),"toBlock":hex(head)}])
print("burns",len(burns),"allTransfers",len(allc),"rpc reqs",len(REQ))
# controls: USDT (known active, known burns)
USDT="0xdAC17F958D2ee523a2206206994597C13D831ec7"
c_all=rpc("eth_getLogs",[{"address":[USDT],"topics":[TRANSFER],"fromBlock":hex(head-200),"toBlock":hex(head)}])
c_burn=rpc("eth_getLogs",[{"address":[USDT],"topics":[TRANSFER,None,ZERO32],"fromBlock":hex(fromB),"toBlock":hex(head)}])
print("control USDT transfers in 200 blocks:",len(c_all),"burns in 14d:",len(c_burn))
out={"pts":{p:maturity_pts[p] for p in pts},"burns":burns,"n_all":len(allc),
     "control_all":len(c_all),"control_burn":len(c_burn)}
json.dump(out,open("scratch/pendle-burn-census.json","w"))
