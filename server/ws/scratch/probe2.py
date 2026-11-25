import subprocess, json
def rpc(method, params):
    r = subprocess.run(["python3","/srv/farm/ws/tools/rpc.py","bsc",method,json.dumps(params)],capture_output=True,text=True)
    try: return json.loads(r.stdout)
    except: return {"err":(r.stdout+r.stderr)[:200]}
def sel(sig):
    return subprocess.run(["cast","sig",sig],capture_output=True,text=True).stdout.strip()
NEW="0x1111111111111111111111111111111111111111"
tests=[("BUSD-ALPACA","0x21125d94Cfe886e7179c8D2fE8c1EA8D57C73E0e"),
       ("CakeLPBDOBUSD","0x985220F21ba808E98246Fb55784BC22B6c790E86"),
       ("bDex_BLP_BNB_BUSD","0x2A0393B3fbf1ddb5843fe55C16143d0668D12145")]
for name,a in tests:
    for fn in ["paused()","earn()","convertDustToEarned()"]:
        d=rpc("eth_call",[{"from":NEW,"to":a,"data":sel(fn)},"latest"])
        if "result" in d: print(name,fn,"OK",d["result"][:20])
        else: print(name,fn,"REVERT:",str(d.get("error",{}).get("message",d))[:80])
