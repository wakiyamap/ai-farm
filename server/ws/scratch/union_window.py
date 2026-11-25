import json
import subprocess
from datetime import datetime, timezone, timedelta


def rpc(method, params):
    out = subprocess.check_output(['python3', '/srv/farm/ws/tools/rpc.py', 'ethereum', method, json.dumps(params)], text=True)
    obj = json.loads(out)
    if 'error' in obj:
        raise RuntimeError(obj['error'])
    return obj['result']


head = int(rpc('eth_blockNumber', []), 16)
head_block = rpc('eth_getBlockByNumber', [hex(head), False])
target = int(datetime.now(timezone.utc).timestamp()) - 7 * 86400
lo, hi = max(0, head - 70000), head
while lo + 1 < hi:
    mid = (lo + hi) // 2
    b = rpc('eth_getBlockByNumber', [hex(mid), False])
    if int(b['timestamp'], 16) < target:
        lo = mid
    else:
        hi = mid
start = rpc('eth_getBlockByNumber', [hex(hi), False])
print(json.dumps({'start_block': hi, 'start_time': datetime.fromtimestamp(int(start['timestamp'], 16), timezone.utc).isoformat(), 'head_block': head, 'head_time': datetime.fromtimestamp(int(head_block['timestamp'], 16), timezone.utc).isoformat(), 'target_time': datetime.fromtimestamp(target, timezone.utc).isoformat()}))
