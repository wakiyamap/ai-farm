import subprocess, json, sys
CRV="0xd533a949740bb3306d119cc777fa900ba034cd52"
TRANSFER="0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
RECEIVER="0x0000000000000000000000008a8e1692478ead0e07f7bb94f78641d57f8bb259"
HEAD=int(sys.argv[1])
start=16500000; step=2000000
hits=[]
lo=start
while lo<HEAD:
    hi=min(lo+step-1,HEAD)
    params=[{"address":CRV,"topics":[TRANSFER,None,RECEIVER],"fromBlock":hex(lo),"toBlock":hex(hi)}]
    r=subprocess.run(["python3","/srv/farm/ws/tools/rpc.py","ethereum","eth_getLogs",json.dumps(params),"--lane","research"],capture_output=True,text=True)
    try:
        logs=json.loads(r.stdout)["result"]
    except Exception:
        print("ERR",lo,hi,r.stdout[:200],r.stderr[:200]); sys.exit(1)
    print(f"{lo}-{hi}: {len(logs)}", [ (int(x['blockNumber'],16), x['transactionHash'][:14], int(x['data'][2:],16)/10**18) for x in logs[:6] ], flush=True)
    if logs: hits+=logs
    lo=hi+1
json.dump(hits,open("scratch/claim_hits_eth.json","w"))
