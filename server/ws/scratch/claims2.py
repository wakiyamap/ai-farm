import subprocess, json, time, hashlib
def rpc(method, params):
    r = subprocess.run(["python3","/srv/farm/ws/tools/rpc.py","ethereum",method,json.dumps(params)],
                       capture_output=True, text=True)
    d = json.loads(r.stdout)
    if "error" in d: print("ERR", method, params[:1] if params else "", d["error"]); return None
    return d["result"]
def f(t): return time.strftime("%Y-%m-%d", time.gmtime(t))
def ts(n): return int(rpc("eth_getBlockByNumber",[hex(n),False])["timestamp"],16)
M="0x6E8B67B315b44519f8C2BEfdbbE11097c45353b4"
S="0xF2c8e860ca12Cde3F3195423eCf54427A4f30916"
def keccak(s):
    out=subprocess.run(["cast","keccak",s],capture_output=True,text=True).stdout.strip()
    return out
print("hex blocks:", hex(19670663), hex(19117697))
for name,addr,sig,frm in [("MaroonedETHClaimed",M,"MaroonedETHClaimed(address,address,uint256)","0x12BDC87"),
                          ("MaroonedETHClaimed",S,"MaroonedETHClaimed(address,address,uint256)","0x1234f61"),
                          ("LockUpsClaimed",M,"LockUpsClaimed(address,address,(uint256,uint256)[])","0x12BDC87"),
                          ("MaroonedETH",M,"MaroonedETH(address,uint256)","0x12BDC87")]:
    t0=keccak(sig)
    logs=rpc("eth_getLogs",[{"address":addr,"topics":[t0],"fromBlock":frm,"toBlock":"latest"}])
    if logs is None: continue
    print(name, addr[:8], "count", len(logs))
    for l in logs[-3:]:
        n=int(l["blockNumber"],16)
        print("   block",n,f(ts(n)),"data",l["data"][:138])
