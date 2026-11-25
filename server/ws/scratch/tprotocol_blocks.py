import datetime
import json
import subprocess


def rpc(method, params):
    p = subprocess.run(
        ["python3", "/srv/farm/ws/tools/rpc.py", "ethereum", method, json.dumps(params)],
        capture_output=True, text=True, check=True,
    )
    obj = json.loads(p.stdout)
    if "error" in obj:
        raise RuntimeError(obj)
    return obj["result"]


head = int(rpc("eth_blockNumber", []), 16)
latest = rpc("eth_getBlockByNumber", [hex(head), False])
target = int(latest["timestamp"], 16) - 7 * 86400
lo, hi = head - 100000, head
while lo + 1 < hi:
    mid = (lo + hi) // 2
    ts = int(rpc("eth_getBlockByNumber", [hex(mid), False])["timestamp"], 16)
    if ts < target:
        lo = mid
    else:
        hi = mid
start = rpc("eth_getBlockByNumber", [hex(hi), False])
for label, blk in [("start", start), ("head", latest)]:
    print(label, int(blk["number"], 16), datetime.datetime.fromtimestamp(int(blk["timestamp"], 16), datetime.timezone.utc).isoformat())
