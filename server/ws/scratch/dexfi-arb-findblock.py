import subprocess, json, sys
def block(n):
    r = subprocess.run(["python3","/srv/farm/ws/tools/rpc.py","arbitrum","eth_getBlockByNumber",
                        json.dumps([hex(n), False])], capture_output=True, text=True)
    return json.loads(r.stdout)["result"]
target = int(sys.argv[1])
lo, hi = 0, int(sys.argv[2])
# get timestamps
while lo < hi:
    mid = (lo + hi) // 2
    ts = int(block(mid)["timestamp"], 16)
    if ts < target: lo = mid + 1
    else: hi = mid
b = block(lo)
print(lo, int(b["timestamp"],16), b["timestamp"])
