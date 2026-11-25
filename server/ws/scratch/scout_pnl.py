import json, subprocess, sys
ADDR="0x302649ccdfc232ee49a28755c8a6c06e707b7d15".lower()
PRICE={"0x833589fcd6edb6e08f4c7c32d4f71b54bda02913":(0.99991,6,"USDC"),
       "0xcbb7c0000ab88b473b1f5afd9ef808440eed33bf":(65109.945,8,"cbBTC"),
       "0x4200000000000000000000000000000000000006":(1818.485,18,"WETH")}
ETH=1818.485
def rpc(method, params):
    out = subprocess.run(["python3","tools/rpc.py","base",method,json.dumps(params),"--lane","research"],
                         capture_output=True, text=True).stdout
    d=json.loads(out)
    if "error" in d: print("ERR", d["error"]["message"][:150]); return None
    return d["result"]
tot_usd=0; tot_gas=0; n=0
for h in sys.argv[1:]:
    r = rpc("eth_getTransactionReceipt",[h])
    if not r: continue
    n+=1
    net={}
    fills=0
    for l in r["logs"]:
        t=l["topics"]
        if t[0]=="0x78ad7ec0e9f89e74012afa58738b6b661c024cb0fd185ee2f616c0a28924bd66": fills+=1
        if len(t)==3 and t[0].startswith("0xddf252ad"):
            frm="0x"+t[1][-40:]; to="0x"+t[2][-40:]; amt=int(l["data"],16)
            c=l["address"].lower()
            if to.lower()==ADDR: net[c]=net.get(c,0)+amt
            if frm.lower()==ADDR: net[c]=net.get(c,0)-amt
    usd=sum(v/10**PRICE.get(c,(1,18,"?"))[1]*PRICE.get(c,(1,18,"?"))[0] for c,v in net.items())
    gas=int(r["gasUsed"],16); gp=int(r["effectiveGasPrice"],16)
    gusd=gas*gp/1e18*ETH
    tot_usd+=usd; tot_gas+=gusd
    parts=" ".join(f"{PRICE.get(c,(c[:6],0,'?'))[2]}{v/10**PRICE.get(c,(1,0,'?'))[1]:+.4f}" for c,v in net.items())
    print(f"{h[:14]} blk{int(r['blockNumber'],16)} fills{fills} gas{gas} gasUSD{gusd:.4f} netUSD{usd:+.4f} | {parts}")
print(f"SAMPLE n={n} avg netUSD {tot_usd/n:+.4f} avg gasUSD {tot_gas/n:.4f} avg net-of-gas {(tot_usd-tot_gas)/n:+.4f}")
