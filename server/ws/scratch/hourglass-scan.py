import datetime
import json
import subprocess

def rpc(method, params):
    p = subprocess.run(['python3', 'tools/rpc.py', 'ethereum', method, json.dumps(params)], capture_output=True, text=True)
    if p.returncode:
        raise RuntimeError(p.stdout + p.stderr)
    o = json.loads(p.stdout)
    if 'error' in o:
        raise RuntimeError(str(o['error']))
    return o['result']

head = rpc('eth_getBlockByNumber', ['latest', False])
hi = int(head['number'], 16)
target = int(head['timestamp'], 16) - 604800
lo = hi - 60000
while lo < hi:
    mid = (lo + hi) // 2
    b = rpc('eth_getBlockByNumber', [hex(mid), False])
    if int(b['timestamp'], 16) < target:
        lo = mid + 1
    else:
        hi = mid
start = rpc('eth_getBlockByNumber', [hex(lo), False])
print(json.dumps({'start_block': lo, 'start_time': datetime.datetime.fromtimestamp(int(start['timestamp'], 16), datetime.timezone.utc).isoformat(), 'end_block': int(head['number'], 16), 'end_time': datetime.datetime.fromtimestamp(int(head['timestamp'], 16), datetime.timezone.utc).isoformat()}))
addr = '0xdfa1f69774ad2924cebd43d75aadfb92403c5335'
topic = '0x70220290ea80981efd0f0f7e6b1b5085605eb976822c8b8422e5bcc53e4c6d63'
for label, filt in [('incentive', {'address': addr, 'topics': [topic]}), ('all', {'address': addr})]:
    filt.update(fromBlock=hex(lo), toBlock=head['number'])
    logs = rpc('eth_getLogs', [filt])
    print(json.dumps({'label': label, 'count': len(logs), 'sample': logs[:5]}))
for name, selector in [('incentiveFXS', '0x45295ada'), ('lockIncentive', '0x50940618'), ('fxs', '0x7d423446')]:
    value = rpc('eth_call', [{'to': addr, 'data': selector}, 'latest'])
    print(json.dumps({'getter': name, 'value': value}))
factory = '0x679619FA685a18782a86dD5850124A75E83daD8F'
for i in range(9):
    value = rpc('eth_call', [{'to': factory, 'data': '0x5c1a738a' + f'{i:064x}'}, 'latest'])
    print(json.dumps({'version': i, 'deployments': int(value, 16)}))
    beacon = rpc('eth_call', [{'to': factory, 'data': '0xc8d31c82' + f'{i:064x}'}, 'latest'])
    beacon_addr = '0x' + beacon[-40:]
    impl = rpc('eth_call', [{'to': beacon_addr, 'data': '0x5c60da1b'}, 'latest'])
    print(json.dumps({'version': i, 'beacon': beacon_addr, 'implementation': '0x' + impl[-40:]}))
