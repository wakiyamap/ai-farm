import json, subprocess
exec(open("/srv/farm/ws/scratch/cian-logs60.py").read().split("# ~60d")[0])
params=json.dumps([{"fromBlock":hex(23500000),"toBlock":hex(26460744),"address":addrs,"topics":[[tCR,tMF]]}])
out=subprocess.run(["python3","/srv/farm/ws/tools/rpc.py","ethereum","eth_getLogs",params],capture_output=True,text=True).stdout
r=json.loads(out)
logs=r.get("result",[])
print("~370d CollectRevenue+CollectManagementFee logs:",len(logs))
for l in logs[:12]:
    print(hex(int(l["blockNumber"],16)), l["address"][:12], l["topics"][0][:10], "raw",int(l["data"],16))
