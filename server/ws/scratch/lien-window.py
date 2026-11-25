import datetime
import json
import subprocess


def rpc(method, params):
    p = subprocess.run(
        ["python3", "/srv/farm/ws/tools/rpc.py", "ethereum", method, json.dumps(params)],
        check=True,
        capture_output=True,
        text=True,
    )
    out = json.loads(p.stdout)
    return out["result"]


head = int(rpc("eth_blockNumber", []), 16)
latest = rpc("eth_getBlockByNumber", [hex(head), False])
target = int(latest["timestamp"], 16) - 7 * 86400
lo, hi = max(0, head - 70000), head
while lo < hi:
    mid = (lo + hi) // 2
    block = rpc("eth_getBlockByNumber", [hex(mid), False])
    if int(block["timestamp"], 16) < target:
        lo = mid + 1
    else:
        hi = mid
start = rpc("eth_getBlockByNumber", [hex(lo), False])
print(json.dumps({
    "start_block": lo,
    "start_time": datetime.datetime.fromtimestamp(int(start["timestamp"], 16), datetime.timezone.utc).isoformat(),
    "head_block": head,
    "head_time": datetime.datetime.fromtimestamp(int(latest["timestamp"], 16), datetime.timezone.utc).isoformat(),
    "start_hex": hex(lo),
    "head_hex": hex(head),
}))
