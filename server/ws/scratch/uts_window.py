#!/usr/bin/env python3
import subprocess, sys, json
RPC = "/srv/farm/ws/tools/rpc.py"

def rpc(method, params):
    p = subprocess.run([sys.executable, RPC, "ethereum", method, json.dumps(params)],
                       capture_output=True, text=True)
    d = json.loads(p.stdout)
    if "error" in d:
        raise SystemExit("rpc error: " + json.dumps(d["error"])[:300])
    return d["result"]

def block(n):
    return rpc("eth_getBlockByNumber", [hex(int(n)), False])

def ts(n):
    return int(block(n)["timestamp"], 16)

def find_block_by_ts(target, lo, hi):
    while lo < hi:
        mid = (lo + hi) // 2
        if ts(mid) < target:
            lo = mid + 1
        else:
            hi = mid
    return lo

if __name__ == "__main__":
    head = int(rpc("eth_blockNumber", [])["result"] if False else rpc("eth_blockNumber", []), 16)
    hb = block(head)
    now = int(hb["timestamp"], 16)
    print("head", head, "ts", now)
    target = now - 7 * 86400
    # ethereum ~12s blocks; estimate then binary search +-4000
    est = head - int(7 * 86400 / 12)
    b = find_block_by_ts(target, est - 6000, est + 6000)
    print("7d-ago block", b, "ts", ts(b), "target", target)
    print("delta_days", (now - ts(b)) / 86400)
