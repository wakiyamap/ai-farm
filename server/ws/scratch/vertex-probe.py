import json, urllib.request, sys

def post(url, batch):
    r = urllib.request.urlopen(urllib.request.Request(url, json.dumps(batch).encode(), {'content-type': 'application/json'}))
    return json.loads(r.read())

if __name__ == '__main__':
    head = int('1f1d400b', 16)
    fromBlock = head - 770000
    addr = sys.argv[2] if len(sys.argv) > 2 else '0x3d1E4662Dc3585aF48C12e1634F04338dfCA5000'
    topic0 = sys.argv[3] if len(sys.argv) > 3 else '0x494f937f5cc892f798248aa831acfb4ad7c4bf35edd8498c5fb431ce1e38b035'
    chain = sys.argv[1] if len(sys.argv) > 1 else 'arbitrum'
    url = 'http://127.0.0.1:8545/%s?lane=research' % chain
    batch = [
        {"jsonrpc": "2.0", "id": 1, "method": "eth_getCode", "params": [addr, "latest"]},
        {"jsonrpc": "2.0", "id": 2, "method": "eth_getLogs", "params": [{"address": addr, "topics": [topic0], "fromBlock": hex(fromBlock), "toBlock": "latest"}]},
    ]
    out = post(url, batch)
    for o in out:
        res = o.get('result')
        if isinstance(res, list):
            print('id', o['id'], 'logs:', len(res))
            for l in res[:5]:
                print(' ', l['blockNumber'], l['data'][:120])
        elif res is None:
            print(o['id'], 'None', o.get('error'))
        else:
            print(o['id'], '->', (res[:60] if isinstance(res, str) else res))
