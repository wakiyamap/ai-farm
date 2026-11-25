import datetime
import json
import subprocess
import time


def block(n):
    out = subprocess.check_output([
        "python3", "/srv/farm/ws/tools/rpc.py", "ethereum", "eth_getBlockByNumber",
        json.dumps([hex(n), False]),
    ], text=True)
    b = json.loads(out)["result"]
    return int(b["timestamp"], 16)


head = int(json.loads(subprocess.check_output([
    "python3", "/srv/farm/ws/tools/rpc.py", "ethereum", "eth_blockNumber", "[]"
], text=True))["result"], 16)
head_ts = block(head)
cutoff = int(time.time()) - 7 * 86400
lo, hi = head - 100_000, head
while lo < hi:
    mid = (lo + hi) // 2
    if block(mid) < cutoff:
        lo = mid + 1
    else:
        hi = mid
print(json.dumps({"start_block": lo, "start_timestamp": block(lo), "start_date": datetime.datetime.fromtimestamp(block(lo), datetime.UTC).isoformat(), "head_block": head, "head_timestamp": head_ts, "head_date": datetime.datetime.fromtimestamp(head_ts, datetime.UTC).isoformat()}))
