import datetime
import json
import subprocess

latest = json.load(open('scratch/complifi-latest.json'))['result']
hi = int(latest['number'], 16)
target = int(latest['timestamp'], 16) - 7 * 86400
lo = hi - 100000

def block(n):
    p = subprocess.run(['python3', '/srv/farm/ws/tools/rpc.py', 'ethereum',
                        'eth_getBlockByNumber', json.dumps([hex(n), False])],
                       capture_output=True, text=True, check=True)
    return json.loads(p.stdout)['result']

while lo + 1 < hi:
    mid = (lo + hi) // 2
    b = block(mid)
    if int(b['timestamp'], 16) < target:
        lo = mid
    else:
        hi = mid

for n in (hi, int(latest['number'], 16)):
    b = block(n) if n == hi else latest
    print(n, datetime.datetime.fromtimestamp(int(b['timestamp'], 16), datetime.timezone.utc).isoformat())
