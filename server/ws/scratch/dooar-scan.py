import json, subprocess, sys, time
def rpc(method, params, tries=3):
    for i in range(tries):
        r = subprocess.run(["python3","/srv/farm/ws/tools/rpc.py","bsc",method,json.dumps(params)],capture_output=True,text=True)
        try:
            d = json.loads(r.stdout)
        except Exception:
            time.sleep(2); continue
        if "result" in d: return d["result"]
        print("ERR", r.stdout[:200], file=sys.stderr); time.sleep(2)
    raise RuntimeError("rpc fail")
info = json.load(open("scratch/dooar-range.json"))
head, seven = info["head"], info["seven"]
start = head - seven
addrs = ["0x5f5d385397095aaed4daffe336f9815ac598dff5","0xba5ae86960fe468ff02d83022c0079670bd8f6a9","0x17db7a395bcc1ec828e732a014dd2a7c43ed30f0"]
topics = {"Swap":"0xd78ad95fa46c994b6551d0da85fc275fe613ce37657fb8d5e3d130840159d822",
 "Mint":"0x4c209b5fc8ad50758f13e2e1088ba56a560dff690a1c6fef26394f4c03821c4f",
 "Burn":"0xdccd412f0b1252819cb1fd330b93224ca42612892bb3f4f789976e6d81936496",
 "Skim":"0xb94331e4420f16b156f53c397a8adcd09481283ee7830f7b688b22858e9db80b"}
rev = {v:k for k,v in topics.items()}
counts = {k:0 for k in topics}
samples = []
senders = {}
b = start
pages = 0
while b <= head:
    e = min(b+4999, head)
    logs = rpc("eth_getLogs",[{"fromBlock":hex(b),"toBlock":hex(e),"address":addrs}])
    pages += 1
    for L in logs:
        t = rev.get(L["topics"][0])
        if t:
            counts[t]+=1
            if len(senders)<10: senders[L["transactionHash"]]=L["address"]
            if t=="Swap" and len(samples)<6: samples.append({"tx":L["transactionHash"],"block":int(L["blockNumber"],16),"pair":L["address"],"log":L})
    b = e+1
json.dump({"pages":pages,"start":start,"head":head,"counts":counts,"swap_samples":samples,"txs_sample":senders}, open("scratch/dooar-scan.json","w"), indent=1)
print("done", counts, "pages", pages)
