import subprocess, json, time
def rpc(method, params):
    r = subprocess.run(["python3","/srv/farm/ws/tools/rpc.py","ethereum",method,json.dumps(params)],
                       capture_output=True, text=True)
    d = json.loads(r.stdout)
    if "error" in d: print("ERR", method, d["error"]); return None
    return d["result"]
def f(t): return time.strftime("%Y-%m-%d", time.gmtime(t))
S="0xF2c8e860ca12Cde3F3195423eCf54427A4f30916"
EPOCH="0x07c9d3a8bea400ee1980880fb7f4e3532e56612ff7e6c67e7096e1b3c20818ff"
logs = rpc("eth_getLogs",[{"address":S,"topics":[EPOCH],"fromBlock":"0x1234f61","toBlock":"latest"}])
tot=0; vals=[]
for l in logs:
    d=l["data"][2:]; w=[d[i:i+64] for i in range(0,len(d),64)]
    dist=int(w[3],16); tot+=dist
    vals.append((int(l["blockNumber"],16), int(w[0],16), dist))
print("EpochEnded n=",len(logs),"first block",vals[0][0],"startedAt",f(vals[0][1]),"distributed",vals[0][2]/1e18)
print("  last block",vals[-1][0],"startedAt(next)",f(vals[-1][1]),"distributed",vals[-1][2]/1e18)
print("  TOTAL distributed ETH over", len(logs),"epochs:", tot/1e18)
vals_sorted=sorted(v[2] for v in vals)
print("  median epoch distribution ETH:", vals_sorted[len(vals_sorted)//2]/1e18, " max:", vals_sorted[-1]/1e18)
cur = rpc("eth_call",[{"to":S,"data":"0xd510336c"},"latest"])  # placeholder
