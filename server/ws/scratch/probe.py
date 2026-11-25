import subprocess, json, re, sys
ADDR = {
 "BUSD-ALPACA":"0x21125d94Cfe886e7179c8D2fE8c1EA8D57C73E0e",
 "CakeLPBDOBUSD":"0x985220F21ba808E98246Fb55784BC22B6c790E86",
 "CakeLPBDOBNB":"0x972Da41a5aF1284f2d5a4EfEea53A3f484f5F5F2",
 "BDOLLAR_CLP_BPDOT_BNB":"0xF63aE636E71Eb9a4008F443d7B79fc46B97bE37e",
 "bDex_BLP_BNB_BUSD":"0x2A0393B3fbf1ddb5843fe55C16143d0668D12145",
 "CakeLPBFIBNB-CAKE":"0x30F63007a90F247C691615a72a97BEdFC9Aa0B13",
 "MDGWBNB-MDG":"0x3551271132078503e67F6090422eb34339E138De",
 "BdollarShare_BLP_SBDO_BUSD":"0xe43A97E71D22d855F0A5cdB93be92C0345628460",
 "CakeLP_CAKE_WBNB-BELT":"0xeA2ccaEc75466cb852f1d518f7f0650360669569",
 "Treasury":"0x15A90e6157a870CD335AF03c6df776d0B1ebf94F",
 "Boardroom":"0x9D39cd20901c88030032073Fb014AaF79D84d2C5",
}
def rpc(method, params):
    r = subprocess.run(["python3","/srv/farm/ws/tools/rpc.py","bsc",method,json.dumps(params)],capture_output=True,text=True)
    try: return json.loads(r.stdout)
    except: return {"err":r.stdout[:200]+r.stderr[:200]}
def sel(sig):
    r = subprocess.run(["cast","sig",sig],capture_output=True,text=True)
    return r.stdout.strip()
for name,a in ADDR.items():
    code = rpc("eth_getCode",[a,"latest"]).get("result","0x")
    out=[name,a,"code_len=%d"%((len(code)-2)//2)]
    for g in ["lastEarnBlock()","wantLockedTotal()","isAutoComp()","notPublic()"]:
        d = rpc("eth_call",[{"to":a,"data":sel(g)},"latest"])
        res = d.get("result")
        if res is None: out.append(g.split('(')[0]+"="+str(d.get("error",{}).get("message",d.get("err","?"))[:40]))
        else:
            v=int(res,16) if len(res)>2 else 0
            out.append(f"{g.split('(')[0]}={v}")
    print(" | ".join(out))
