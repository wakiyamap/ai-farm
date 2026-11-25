import subprocess, json, time
def rpc(method, params):
    r = subprocess.run(["python3","/srv/farm/ws/tools/rpc.py","ethereum",method,json.dumps(params)],
                       capture_output=True, text=True)
    d = json.loads(r.stdout)
    if "error" in d: print("ERR", method, d["error"]); return None
    return d["result"]
def ts(n): return int(rpc("eth_getBlockByNumber",[hex(n),False])["timestamp"],16)
def f(t): return time.strftime("%Y-%m-%d", time.gmtime(t))
S="0xF2c8e860ca12Cde3F3195423eCf54427A4f30916"
CLAIMED="0xfc85082516ca8fe95d78404d69723bc9f7f40661fbf2ea20dbdb14c2413d5ea6"
logs = rpc("eth_getLogs",[{"address":S,"topics":[CLAIMED],"fromBlock":"0x1234f61","toBlock":"latest"}])
print("Claimed events since creation:", len(logs))
for l in logs[-5:]:
    n=int(l["blockNumber"],16); d= l["data"][2:]
    words=[d[i:i+64] for i in range(0,len(d),64)]
    print("  block",n,f(ts(n)),"caller",l["topics"][1][-40:],"receiver",l["topics"][2][-40:],"rewards_ETH",int(words[-1],16)/1e18)
