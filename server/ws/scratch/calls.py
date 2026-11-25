import subprocess, json
FRESH="0x1111111111111111111111111111111111111111"
BWQ="0xc6a3f3278c94d04d650b2f0df985994236d404ff"
THR="0x307b99ddae73137343addc6d5bcfd472e89d6f88"
EXM="0xa9febd95da4bdd8946242721e4723325360ba4ae"
def sig(s):
    return subprocess.run(["cast","sig",s],capture_output=True,text=True).stdout.strip()
def call(to,data):
    p=json.dumps([{"from":FRESH,"to":to,"data":data},"latest"])
    o=subprocess.run(["python3","tools/rpc.py","hyperevm","eth_call",p,"--lane","research"],capture_output=True,text=True)
    try:
        d=json.loads(o.stdout)
    except Exception:
        return "ERR "+o.stdout[:200]+o.stderr[:200]
    if "error" in d:
        e=d["error"]
        return "revert: "+(e.get("data","")[:74] if isinstance(e.get("data"),str) else str(e)[:150])
    return "OK ret="+d["result"][:80]
tests=[
 ("BWQ.processBlockedWithdrawals(1)", BWQ, sig("processBlockedWithdrawals(uint256)")+"0"*63+"1"),
 ("BWQ.processBlockedWithdrawals(0)", BWQ, sig("processBlockedWithdrawals(uint256)")+"0"*64),
 ("BWQ.confirmBlockedWithdrawal(1,[])", BWQ, sig("confirmBlockedWithdrawal(uint256,uint256[])")+"0"*63+"1"+"0"*63+"20"),
 ("Throttle.sweep()", THR, sig("sweep()")),
 ("EXM.unwind()", EXM, sig("unwind()")),
 ("EXM.confirmWithdrawal(1,fresh)", EXM, sig("confirmWithdrawal(uint256,address)")+"0"*63+"1"+"0"*44+FRESH[2:]),
 ("BWQ.processableShares()", BWQ, sig("processableShares()")),
 ("BWQ.totalBlockedQueue()", BWQ, sig("totalBlockedQueue()")),
]
for name,to,data in tests:
    print(name, "->", call(to,data))
