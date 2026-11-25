import subprocess, json, sys
CRV="0xd533a949740bb3306d119cc777fa900ba034cd52"
TRANSFER="0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
def pad(h): return "0x"+h[2:].rjust(64,"0")
V1=pad("0x204f41c2753e47b400")   # 596.00686997e18
V2=pad("0x508095a3fbffbc734d")   # 1485.005018007871451981e18
HEAD=26398957; step=2000000
# positive control: recent no-topics window
params=[{"address":CRV,"fromBlock":hex(HEAD-1000),"toBlock":hex(HEAD)}]
r=subprocess.run(["python3","/srv/farm/ws/tools/rpc.py","ethereum","eth_getLogs",json.dumps(params),"--lane","research"],capture_output=True,text=True)
print("control 20k blocks no-topics:", len(json.loads(r.stdout)["result"]))
hits={}
lo=16000000
while lo<HEAD:
    hi=min(lo+step-1,HEAD)
    for tag,VAL in [("mint596",V1),("claim1485",V2)]:
        params=[{"address":CRV,"topics":[TRANSFER,None,None,VAL],"fromBlock":hex(lo),"toBlock":hex(hi)}]
        r=subprocess.run(["python3","/srv/farm/ws/tools/rpc.py","ethereum","eth_getLogs",json.dumps(params),"--lane","research"],capture_output=True,text=True)
        try:
            logs=json.loads(r.stdout)["result"]
        except Exception:
            print("ERR",lo,hi,tag,r.stdout[:200],r.stderr[:200]); sys.exit(1)
        if logs:
            hits[tag]=hits.get(tag,0)+len(logs)
            for h in logs: print("HIT",tag,"block",int(h["blockNumber"],16),"tx",h["transactionHash"])
    lo=hi+1
print("hits:",hits)
