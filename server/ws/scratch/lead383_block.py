import subprocess, json, sys
def ts(num):
    out = subprocess.run(['python3','/srv/farm/ws/tools/rpc.py','base','eth_getBlockByNumber',
        json.dumps([hex(num), False])], capture_output=True, text=True).stdout
    return int(json.loads(out)['result']['timestamp'], 16)
target = 1794714406
lo, hi = 57500000, 57750000
while lo < hi:
    mid = (lo + hi) // 2
    t = ts(mid)
    if t < target: lo = mid + 1
    else: hi = mid
print('B7d', lo, ts(lo), ts(lo-1))
