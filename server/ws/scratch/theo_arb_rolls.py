import subprocess, json, time
def rpc(method, params):
    r = subprocess.run(["python3","/srv/farm/ws/tools/rpc.py","arbitrum",method,json.dumps(params)],
                       capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        return ("ERR", (r.stdout + r.stderr).strip()[:300])
    try: return ("OK", json.loads(r.stdout).get("result"))
    except Exception: return ("ERR", r.stdout[:300])

HEAD=526599984
# 30d ago: nitro ~250ms -> ~10.4M blocks; find via timestamp bsearch
now=int(time.time()); target=now-30*86400
lo,hi=HEAD-12_000_000,HEAD
while lo<hi:
    mid=(lo+hi)//2
    st,b=rpc("eth_getBlockByNumber",[hex(mid),False])
    if int(b["timestamp"],16)<target: lo=mid+1
    else: hi=mid
B30=lo
st,b=rpc("eth_getBlockByNumber",[hex(B30),False])
print("30d block:", B30, time.strftime("%F", time.gmtime(int(b["timestamp"],16))))
st,logs=rpc("eth_getLogs",[{"address":["0x4fE17dEFc597cC3bD6fBe16135d8Ac42D421907e","0xF37Fe9396Bb95f7823A29090c939847f1817bC8a","0x3ca8F12D7B376E9Ef338d1C432CA1b51DD319009","0x54602E5cBa09e01EeE9B2050F1F4f0Dc902CeE34"],
  "topics":["0x509ab3a60bcf0e5158f6bdabea90d540867b8a80428adae5bad92fe0a7e604d1"],
  "fromBlock":hex(B30),"toBlock":hex(HEAD)}])
print("RollRound 30d:", st, len(logs) if st=="OK" else logs[:200])
if st=="OK":
    for l in logs[-5:]:
        print(int(l["blockNumber"],16), l["address"][:10], l["transactionHash"][:14])
