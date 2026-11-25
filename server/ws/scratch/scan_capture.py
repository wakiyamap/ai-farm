import subprocess, json, sys
CRV="0x8ee73c484a26e0a5df2ee2a4960b789967dd0415"
TRANSFER="0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
VAL="0x0000000000000000000000000000000000000000000000204f41c2753e480000"  # 596.00686997e18
start,end,step=13369000,56348000,2000000
hits=[]
lo=start
while lo<end:
    hi=min(lo+step-1,end)
    params=[{"address":CRV,"topics":[TRANSFER,None,None,VAL],"fromBlock":hex(lo),"toBlock":hex(hi)}]
    r=subprocess.run(["python3","/srv/farm/ws/tools/rpc.py","base","eth_getLogs",json.dumps(params),"--lane","research"],capture_output=True,text=True)
    try:
        logs=json.loads(r.stdout)["result"]
    except Exception as e:
        print("ERR",lo,hi,r.stdout[:300],r.stderr[:300]); sys.exit(1)
    print(f"{lo}-{hi}: {len(logs)}")
    if logs: hits+=logs
    lo=hi+1
json.dump(hits,open("scratch/capture_hits.json","w"))
for h in hits:
    print("HIT block",int(h["blockNumber"],16),"tx",h["transactionHash"],"log",h["logIndex"])
