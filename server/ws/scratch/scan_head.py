import subprocess, json
CRV="0x8ee73c484a26e0a5df2ee2a4960b789967dd0415"
HEAD=56693458-5000
lo=HEAD-1000000
params=[{"address":CRV,"fromBlock":hex(lo),"toBlock":"latest"}]
r=subprocess.run(["python3","/srv/farm/ws/tools/rpc.py","base","eth_getLogs",json.dumps(params),"--lane","research","--out","scratch/crv_head_logs.json"],capture_output=True,text=True)
print(r.stdout[:200], r.stderr[:200])
logs=json.load(open("scratch/crv_head_logs.json"))
print("logs",len(logs))
from collections import Counter
pairs=Counter()
for h in logs:
    v=int(h["data"][2:],16)/10**18
    pairs[(h["topics"][1][26:34],h["topics"][2][26:34],round(v,2))]+=1
big=sorted(logs, key=lambda h:-int(h["data"][2:],16))[:15]
for h in big:
    print(int(h["blockNumber"],16), "from", h["topics"][1][24:],"to", h["topics"][2][24:], round(int(h["data"][2:],16)/10**18,2), h["transactionHash"][:18])
