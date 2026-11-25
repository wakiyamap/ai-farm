import subprocess, json, sys, time
def rpc(method, params):
    out = subprocess.run(["python3","/srv/farm/ws/tools/rpc.py","ethereum",method,json.dumps(params)],
                         capture_output=True, text=True).stdout
    return json.loads(out)["result"]
def bno(n):
    return int(rpc("eth_getBlockByNumber",[hex(n) if n!="latest" else n, False])["timestamp"],16)
target = int(time.time()) - 7*86400
lo, hi = 1, int(rpc("eth_blockNumber",[]),16)
head_ts = bno(hi)
print("head", hi, head_ts, time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime(head_ts)))
while lo < hi:
    mid = (lo+hi)//2
    if bno(mid) < target: lo = mid+1
    else: hi = mid
print("7d-ago block", lo, bno(lo), time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime(bno(lo))))
print("span blocks", hi-lo)
