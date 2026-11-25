#!/usr/bin/env python3
"""Tiny helper: call rpc.py avalanche and decode the result with cast."""
import json, subprocess, sys

CHAIN = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith('0x') else 'avalanche'


def rpc(method, params):
    out = subprocess.run(
        ['python3', '/srv/farm/ws/tools/rpc.py', CHAIN, method, json.dumps(params)],
        capture_output=True, text=True)
    txt = out.stdout.strip()
    if not txt:
        return {'error': (out.stderr.strip() or 'empty output')[:300]}
    try:
        return json.loads(txt)
    except Exception:
        return {'error': txt[:300]}


def call(to, sig, *args, decode=None):
    cmd = ['cast', 'calldata', sig] + [str(a) for a in args]
    d = subprocess.run(cmd, capture_output=True, text=True).stdout.strip()
    r = rpc('eth_call', [{'to': to, 'data': d}, 'latest'])
    if 'error' in r:
        return f'ERR {r["error"]}'
    raw = r['result']
    if decode:
        p = subprocess.run(['cast', 'abi-decode', decode, raw], capture_output=True, text=True)
        return (p.stdout.strip() or p.stderr.strip()[:200])
    return raw


if __name__ == '__main__':
    spec = sys.argv[2:]
    for item in spec:
        parts = item.split('|')
        to = parts[0]
        sig = parts[1]
        args = parts[2:] if len(parts) > 2 else []
        dec = None
        if args and args[-1].startswith('@'):
            dec = args[-1][1:]
            args = args[:-1]
        print(f'{to[:10]}.. {sig} {args}'.ljust(60), call(to, sig, *args, decode=dec))
