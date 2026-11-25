import json, subprocess, sys
ADDR="0x302649ccdfc232ee49a28755c8a6c06e707b7d15".lower()
P={"0x833589fcd6edb6e08f4c7c32d4f71b54bda02913":(0.99991,6,"USDC"),
   "0xcbb7c0000ab88b473b1f5afd9ef808440eed33bf":(65109.945,8,"cbBTC"),
   "0x4200000000000000000000000000000000000006":(1818.485,18,"WETH")}
ETH=1818.485
def rpc(m,p):
    o=subprocess.run(["python3","tools/rpc.py","base",m,json.dumps(p),"--lane","research"],capture_output=True,text=True).stdout
    d=json.loads(o)
    if "error" in d: print("ERR",d["error"]["message"][:120]); return None
    return d["result"]
rows=[]
for h in sys.argv[1:]:
    r=rpc("eth_getTransactionReceipt",[h])
    if not r: continue
    inn={}; out={}
    for l in r["logs"]:
        t=l["topics"]
        if len(t)==3 and t[0].startswith("0xddf252ad"):
            frm="0x"+t[1][-40:]; to="0x"+t[2][-40:]; amt=int(l["data"],16); c=l["address"].lower()
            if to.lower()==ADDR: inn[c]=inn.get(c,0)+amt
            if frm.lower()==ADDR: out[c]=out.get(c,0)+amt
    vin=sum(v/10**P[c][1]*P[c][0] for c,v in inn.items() if c in P)
    vout=sum(v/10**P[c][1]*P[c][0] for c,v in out.items() if c in P)
    gas=int(r["gasUsed"],16); g=gas*int(r["effectiveGasPrice"],16)/1e18*ETH
    rows.append((vin,vout,gas,g))
    print(f"{h[:14]} in ${vin:10.2f} out ${vout:10.2f} spread ${vin-vout:+8.4f} gas {gas} ${g:.4f}")
if rows:
    vin=[r[0] for r in rows]
    print(f"n={len(rows)} median gross ${sorted(vin)[len(vin)//2]:.0f} mean ${sum(vin)/len(vin):.0f} mean spread ${sum(r[0]-r[1] for r in rows)/len(rows):+.4f} mean gas ${sum(r[3] for r in rows)/len(rows):.4f}")
