import subprocess, json, sys
CRV="0x8ee73c484a26e0a5df2ee2a4960b789967dd0415"
TRANSFER="0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
def pad(h): return "0x"+h[2:].rjust(64,"0")
V1=pad("0x204f41c2753e47b400"); V2=pad("0x508095a3fbffbc734d")
lo,hi=13238000,13369000
for tag,VAL in [("mint596",V1),("claim1485",V2)]:
    params=[{"address":CRV,"topics":[TRANSFER,None,None,VAL],"fromBlock":hex(lo),"toBlock":hex(hi)}]
    r=subprocess.run(["python3","/srv/farm/ws/tools/rpc.py","base","eth_getLogs",json.dumps(params),"--lane","research"],capture_output=True,text=True)
    try: logs=json.loads(r.stdout)["result"]
    except Exception: print("ERR",tag,r.stdout[:300],r.stderr[:200]); sys.exit(1)
    print(tag,len(logs))
    for h in logs: print("  block",int(h["blockNumber"],16),"tx",h["transactionHash"],"from",h["topics"][1][24:44],"to",h["topics"][2][24:44])
# control: any Transfer in the bracket (no topics)
params=[{"address":CRV,"fromBlock":hex(lo),"toBlock":hex(hi)}]
r=subprocess.run(["python3","/srv/farm/ws/tools/rpc.py","base","eth_getLogs",json.dumps(params),"--lane","research"],capture_output=True,text=True)
try:
    logs=json.loads(r.stdout)["result"]; print("control no-topics 13.238-13.369M:", len(logs))
except Exception: print("ctrl ERR", r.stdout[:300])
