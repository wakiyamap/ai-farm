#!/usr/bin/env python3
"""Small helper: call the farm RPC relay for ethereum from python."""
import json, subprocess

def rpc(method, params):
    out = subprocess.run(
        ['python3', '/srv/farm/ws/tools/rpc.py', 'ethereum', method, json.dumps(params)],
        capture_output=True, text=True).stdout
    d = json.loads(out)
    if 'error' in d:
        raise SystemExit(f'RPC error for {method}: {json.dumps(d["error"])[:300]}')
    return d['result']

def blk(n):
    d = rpc('eth_getBlockByNumber', ['%#x' % n, False] if isinstance(n, int) else [n, False])
    return int(d['number'], 16), int(d['timestamp'], 16)

def head():
    return int(rpc('eth_blockNumber', []), 16)

def block_at_time(target):
    """First block with timestamp >= target (estimate 12 s blocks, then bracket)."""
    h_num, h_ts = blk(head())
    n = max(0, h_num - int((h_ts - target) / 12))
    _, ts = blk(n)
    if ts < target:
        lo, hi = n, h_num
    else:
        hi, lo = n, max(0, n - 200000)
    while lo < hi:
        mid = (lo + hi) // 2
        _, tsm = blk(mid)
        if tsm < target:
            lo = mid + 1
        else:
            hi = mid
    return lo
