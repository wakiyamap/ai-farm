import subprocess, json
MID = "0x4d776c433ec7b43a72ca5454dfebf010f70795d344e53e7a2f1d6cd4610177e3"
FACT = "0x188a8CFa039C049c6B076C52164E5d51ee207a98"
sel = subprocess.run(["cast","sig","getMarketContracts(bytes32)"],capture_output=True,text=True).stdout.strip()
data = sel + MID[2:]
params = json.dumps([{"to":FACT,"data":data},"latest"])
out = subprocess.run(["python3","tools/rpc.py","hyperevm","eth_call",params,"--lane","research"],capture_output=True,text=True)
d = json.loads(out.stdout)
r = d["result"][2:]
names=['router','exManager','exLST','stakingAccountant','validatorManager','oracleManager','rewardShareTracker','ghostLST','bwq','defaultOracle','oracleAdapter','launchFeeSplitter','stakeFeesThrottle']
for i,n in enumerate(names):
    print(n, "0x"+r[i*64+24:i*64+64])
