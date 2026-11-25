import subprocess, json, time
def rpc(method, params):
    r = subprocess.run(["python3","/srv/farm/ws/tools/rpc.py","ethereum",method,json.dumps(params)],
                       capture_output=True, text=True)
    d = json.loads(r.stdout)
    if "error" in d: print("ERR", method, d["error"]); return None
    return d["result"]
def ts(n):
    b = rpc("eth_getBlockByNumber",[hex(int(n,16) if isinstance(n,str) else n),False])
    return int(b["timestamp"],16)
def f(t): return time.strftime("%Y-%m-%d", time.gmtime(t))
S="0xF2c8e860ca12Cde3F3195423eCf54427A4f30916"
M="0x6E8B67B315b44519f8C2BEfdbbE11097c45353b4"
EPOCH="0x07c9d3a8bea400ee1980880fb7f4e3532e56612ff7e6c67e7096e1b3c20818ff"
DEP="0x67dfb2bd87d8afa1e2cf4efc2037c61e5991810ed043680f54f54736a3da85aa"
E="0x1234f61"  # creation block 19117697
logs = rpc("eth_getLogs",[{"address":S,"topics":[EPOCH],"fromBlock":E,"toBlock":"latest"}])
print("EpochEnded count since creation:", len(logs))
for l in logs[-4:]:
    print("  epoch log block", int(l["blockNumber"],16), f(ts(l["blockNumber"])), "distributed", int(l["data"],16)/1e18, "ETH")
dep = rpc("eth_getLogs",[{"address":S,"topics":[DEP],"fromBlock":E,"toBlock":"latest"}])
print("Deposited count:", len(dep))
for l in dep[-3:]:
    print("  Deposited block", int(l["blockNumber"],16), f(ts(l["blockNumber"])))
for name,a in [("market",M),("staking",S)]:
    bal = int(rpc("eth_getBalance",[a,"latest"]),16)
    print(name, "ETH balance", bal/1e18)
cur = rpc("eth_call",[{"to":S,"data":"0x"+"$(true)"}, "latest"])
