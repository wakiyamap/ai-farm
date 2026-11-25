import datetime as dt
import json
import subprocess


def rpc(method, params):
    out = subprocess.run(
        ["python3", "/srv/farm/ws/tools/rpc.py", "ethereum", method, json.dumps(params)],
        capture_output=True, text=True,
    )
    data = json.loads(out.stdout)
    if "error" in data:
        raise RuntimeError(data["error"])
    return data["result"]


def block(number):
    result = rpc("eth_getBlockByNumber", [hex(number), False])
    return int(result["timestamp"], 16)


head = int(rpc("eth_blockNumber", []), 16)
head_time = block(head)
target = head_time - 7 * 86400
lo, hi = head - 60000, head
while lo + 1 < hi:
    mid = (lo + hi) // 2
    if block(mid) < target:
        lo = mid
    else:
        hi = mid
print(json.dumps({
    "from_block": hi,
    "from_timestamp": block(hi),
    "from_iso": dt.datetime.fromtimestamp(block(hi), dt.timezone.utc).isoformat(),
    "head_block": head,
    "head_timestamp": head_time,
    "head_iso": dt.datetime.fromtimestamp(head_time, dt.timezone.utc).isoformat(),
}))
