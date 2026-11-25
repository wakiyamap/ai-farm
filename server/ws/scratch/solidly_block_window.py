import datetime
import json
import subprocess
import time


def rpc(method, params):
    p = subprocess.run(
        ["python3", "/srv/farm/ws/tools/rpc.py", "ethereum", method, json.dumps(params)],
        capture_output=True, text=True, check=True,
    )
    obj = json.loads(p.stdout)
    if "error" in obj:
        raise RuntimeError(obj["error"])
    return obj["result"]


target = int(time.time()) - 7 * 86400
head = int(rpc("eth_blockNumber", []), 16)
lo, hi = head - 100000, head
while lo < hi:
    mid = (lo + hi) // 2
    b = rpc("eth_getBlockByNumber", [hex(mid), False])
    if int(b["timestamp"], 16) < target:
        lo = mid + 1
    else:
        hi = mid
for n in (lo, head):
    b = rpc("eth_getBlockByNumber", [hex(n), False])
    print(n, datetime.datetime.fromtimestamp(int(b["timestamp"], 16), datetime.timezone.utc).isoformat(), hex(n))
