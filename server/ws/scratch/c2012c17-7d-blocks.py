import datetime
import json
import os
import sys
import urllib.request

relay = os.environ['RPC_RELAY_URL'].rstrip('/')
cutoff = int(datetime.datetime.now(datetime.timezone.utc).timestamp()) - 7 * 86400


def rpc(chain, method, params):
    req = urllib.request.Request(
        f'{relay}/{chain}?lane=research',
        json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params}).encode(),
        {'Content-Type': 'application/json'},
    )
    data = json.load(urllib.request.urlopen(req, timeout=60))
    if 'error' in data:
        raise RuntimeError(data['error'])
    return data['result']


for chain in sys.argv[1:]:
    head = int(rpc(chain, 'eth_blockNumber', []), 16)
    lo, hi = 0, head
    while lo < hi:
        mid = (lo + hi) // 2
        block = rpc(chain, 'eth_getBlockByNumber', [hex(mid), False])
        if int(block['timestamp'], 16) < cutoff:
            lo = mid + 1
        else:
            hi = mid
    print(json.dumps({'chain': chain, 'head': head, 'start': lo,
                      'blocks': head - lo, 'cutoff_utc': datetime.datetime.fromtimestamp(
                          cutoff, datetime.timezone.utc).isoformat()}), flush=True)
