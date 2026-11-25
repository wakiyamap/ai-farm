import json, subprocess, sys
RPC=["python3","/srv/farm/ws/tools/rpc.py","hyperevm","eth_getLogs"]
latest=0x3123288
start=latest-604800
CLAIM="0x2d43eb174787155132b52ddb6b346e2dca99302eac3df4466dbeff953d3c84d1"
FIN="0x8cc85b3d50ab2fb4e96570e702130699f959c4eb55d235f563f02ca5400d3c2a"
QUEUED="0xa2bc034e3400735d5038171f4a52ede4ca8a21acc010aab81996a18301cdf0a3"
WM="0x9d0B0877b9f2204CF414Ca7862E4f03506822538"
# 12 windows of 1000 blocks, evenly spaced across 7d
step=(latest-start)//12
tot={"claim":0,"fin":0,"queued":0}
per=[]
for i in range(12):
    a=start+i*step
    params=[{"fromBlock":hex(a),"toBlock":hex(a+999),"address":WM,"topics":[[CLAIM,FIN,QUEUED]]}]
    r=subprocess.run(RPC+[json.dumps(params),"--lane","research"],capture_output=True,text=True)
    try:
        logs=json.loads(r.stdout)["result"]
    except Exception as e:
        per.append((a,"ERR",r.stdout[:80]+r.stderr[:80])); continue
    c=sum(1 for l in logs if l["topics"][0].lower()==CLAIM.lower())
    f=sum(1 for l in logs if l["topics"][0].lower()==FIN.lower())
    q=sum(1 for l in logs if l["topics"][0].lower()==QUEUED.lower())
    tot["claim"]+=c; tot["fin"]+=f; tot["queued"]+=q
    per.append((a,c,f,q))
print("windows (block, claim, finalized, queued):")
for p in per: print(" ",p)
print("TOTAL over sampled", 12*1000, "blocks of", latest-start, ":", tot)
