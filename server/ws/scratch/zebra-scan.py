import json, subprocess, sys
RPC=["python3","/srv/farm/ws/tools/rpc.py","base","eth_getLogs"]
ADDR=["0x798937a81cea1cc124545210b6b45719516b3e42","0xbdebd38133a19aaf213836cf4b1c81a5013321fc",
      "0x9e3bc013f09c8bca4b52a7d29c236352021f7a96","0x8b51143530a92f703c954ab0d261ef688d9d93f1",
      "0xe7576878421ba6d0f5f6e13979fd96994a3fa8b8","0x4b20dbdd4d5a7a762f788796df5e0487007c6b36"]
def getlogs(addrs, topic, a, b):
    p=[[{"fromBlock":hex(a),"toBlock":hex(b),"address":addrs,"topics":[topic]}]][0]
    r=subprocess.run(RPC+["--params-file","/dev/stdin"], input=json.dumps(p), capture_output=True, text=True)
    try:
        d=json.loads(r.stdout)
    except Exception:
        return None, (r.stdout[:200]+r.stderr[:200])
    if "error" in d: return None, json.dumps(d["error"])[:200]
    return d["result"], None
if __name__=="__main__":
    topic=sys.argv[1]; latest=int(sys.argv[2]); span=int(sys.argv[3]); step=45000
    out=[]; errs=0
    b=latest
    while b > latest-span:
        a=max(latest-span, b-step)
        res, err = getlogs(ADDR, topic, a, b)
        if err: errs+=1; print("ERR", a, b, err, file=sys.stderr)
        else: out += res
        b=a
    print(json.dumps({"topic":topic,"from":latest-span,"to":latest,"count":len(out),"errors":errs,"logs":out}))
