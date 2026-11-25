import json
import subprocess
import datetime

target = 1794871256
def block(n):
    cmd = ['python3', 'tools/rpc.py', 'ethereum', 'eth_getBlockByNumber', json.dumps([hex(n), False])]
    p = subprocess.run(cmd, capture_output=True, text=True, check=True)
    b = json.loads(p.stdout)['result']
    return int(b['timestamp'], 16)

head_cmd = ['python3', 'tools/rpc.py', 'ethereum', 'eth_blockNumber', '[]']
head = int(json.loads(subprocess.run(head_cmd, capture_output=True, text=True, check=True).stdout)['result'], 16)
lo, hi = head - 100000, head
while lo < hi:
    mid = (lo + hi) // 2
    if block(mid) < target:
        lo = mid + 1
    else:
        hi = mid
for n in (lo, head):
    ts = block(n)
    print(n, datetime.datetime.fromtimestamp(ts, datetime.timezone.utc).isoformat())
