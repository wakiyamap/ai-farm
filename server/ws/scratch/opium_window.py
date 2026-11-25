import datetime
import json
import subprocess

target = int(datetime.datetime(2026, 11, 16, 23, 12, 28, tzinfo=datetime.timezone.utc).timestamp())

def rpc(method, params):
    out = subprocess.check_output(['python3', '/srv/farm/ws/tools/rpc.py', 'ethereum', method, json.dumps(params)], text=True)
    return json.loads(out)['result']

head = int(rpc('eth_blockNumber', []), 16)
lo, hi = head - 100000, head
while lo + 1 < hi:
    mid = (lo + hi) // 2
    block = rpc('eth_getBlockByNumber', [hex(mid), False])
    if int(block['timestamp'], 16) < target:
        lo = mid
    else:
        hi = mid
for n in (lo, hi, head):
    block = rpc('eth_getBlockByNumber', [hex(n), False])
    ts = int(block['timestamp'], 16)
    print(n, datetime.datetime.fromtimestamp(ts, datetime.timezone.utc).isoformat())
