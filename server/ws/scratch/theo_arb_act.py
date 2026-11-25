import subprocess, json, time

def rpc(method, params):
    r = subprocess.run(["python3","/srv/farm/ws/tools/rpc.py","arbitrum",method,json.dumps(params)],
                       capture_output=True, text=True, timeout=90)
    if r.returncode != 0:
        return ("ERR", (r.stdout + r.stderr).strip()[:300])
    try: return ("OK", json.loads(r.stdout).get("result"))
    except Exception: return ("ERR", r.stdout[:300])

now = int(time.time())
st, head = rpc("eth_blockNumber", [])
head = int(head, 16)
print("head:", head)
# find block at now - 7d by binary search on timestamps (nitro ~250ms blocks; use getBlockByNumber sparse)
lo, hi = head - 3_500_000, head
st, hb = rpc("eth_getBlockByNumber", [hex(head), False])
head_ts = int(hb["timestamp"], 16)
target = now - 7*86400
print("head_ts:", head_ts, time.strftime("%F %T", time.gmtime(head_ts)))
while lo < hi:
    mid = (lo + hi) // 2
    st, b = rpc("eth_getBlockByNumber", [hex(mid), False])
    ts = int(b["timestamp"], 16)
    if ts < target: lo = mid + 1
    else: hi = mid
start = lo
st, b = rpc("eth_getBlockByNumber", [hex(start), False])
print("7d-ago block:", start, time.strftime("%F %T", time.gmtime(int(b["timestamp"],16))))

VAULTS = {
 "0x4fE17dEFc597cC3bD6fBe16135d8Ac42D421907e": "TETH42161",
 "0xF37Fe9396Bb95f7823A29090c939847f1817bC8a": "TUSDC42161",
 "0x3ca8F12D7B376E9Ef338d1C432CA1b51DD319009": "TUSDCH42161",
 "0x54602E5cBa09e01EeE9B2050F1F4f0Dc902CeE34": "maweETH_Theo",
}
for a, name in VAULTS.items():
    st, logs = rpc("eth_getLogs", [{"address": a, "fromBlock": hex(start), "toBlock": hex(head)}])
    print(name, "7d logs:", "ERR:"+st[1] if st=="ERR" else len(logs))
