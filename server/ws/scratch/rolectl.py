import subprocess, json
FRESH="0x1111111111111111111111111111111111111111"
ORACLE="0x49ea44f34d2218f40371b2f093b8523f78a93652"
ORGM="0x2afcd10cee247e5cdb50f1d8b0f7dfe3b45586bc"
def sig(s): return subprocess.run(["cast","sig",s],capture_output=True,text=True).stdout.strip()
def call(to,data):
    p=json.dumps([{"from":FRESH,"to":to,"data":data},"latest"])
    o=subprocess.run(["python3","tools/rpc.py","hyperevm","eth_call",p,"--lane","research"],capture_output=True,text=True)
    d=json.loads(o.stdout)
    if "error" in d:
        e=d["error"]; dat=e.get("data")
        return "revert "+(dat if isinstance(dat,str) else json.dumps(e))[:120]
    return "OK "+d["result"][:70]
V="000000000000000000000000"+"376954f95c0b9d31bd8817af359cab03c84d202c"
print("DefaultOracle.updateValidatorMetrics(from fresh):", call(ORACLE, sig("updateValidatorMetrics(address,uint256,uint256,uint256,uint256,uint256)")+V+"0"*64*5))
print("OracleManager.generatePerformance(from fresh):", call(ORGM, sig("generatePerformance(address)")+V))
# control: a known-active callable on another protocol (Delpho DSM liquidate per KB 1631)
