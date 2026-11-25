import subprocess, json, sys
CRV="0x8ee73c484a26e0a5df2ee2a4960b789967dd0415"
TRANSFER="0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
RECEIVER="0x0000000000000000000000008a8e1692478ead0e07f7bb94f78641d57f8bb259"
VALUE2="0x00000000000000000000000000000000000000000000000508095a3fbffbc734d"  # 1485.005018007871451981e18
start,end,step=13238000,56348000,2000000
hits=[]
lo=start
while lo<end:
    hi=min(lo+step-1,end)
    params=[{"address":CRV,"topics":[TRANSFER,None,RECEIVER],"fromBlock":hex(lo),"toBlock":hex(hi)}]
    r=subprocess.run(["python3","/srv/farm/ws/tools/rpc.py","base","eth_getLogs",json.dumps(params),"--lane","research"],capture_output=True,text=True)
    try:
        logs=json.loads(r.stdout)["result"]
    except Exception:
        print("ERR",lo,hi,r.stdout[:300],r.stderr[:200]); sys.exit(1)
    print(f"{lo}-{hi}: {len(logs)}", [ (int(x['blockNumber'],16), x['transactionHash'][:12], int(x['data'][2:],16)/10**18) for x in logs[:4] ], flush=True)
    if logs: hits+=logs
    lo=hi+1
json.dump(hits,open("scratch/claim_hits.json","w"))
