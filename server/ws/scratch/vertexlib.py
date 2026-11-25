import json, urllib.request

def post(chain, batch, lane='research'):
    url = 'http://127.0.0.1:8545/%s?lane=%s' % (chain, lane)
    req = urllib.request.Request(url, json.dumps(batch).encode(), {'content-type': 'application/json'})
    return json.loads(urllib.request.urlopen(req).read())

def head_of(chain):
    return int(post(chain, [{"jsonrpc": "2.0", "id": 1, "method": "eth_blockNumber", "params": []}])[0]['result'], 16)

if __name__ == '__main__':
    topic0 = '0x494f937f5cc892f798248aa831acfb4ad7c4bf35edd8498c5fb431ce1e38b035'
    for chain, span in (('arbitrum', 300000), ('base', 500000)):
        head = head_of(chain)
        frm = head - span
        o = post(chain, [{"jsonrpc": "2.0", "id": 2, "method": "eth_getLogs",
                          "params": [{"topics": [topic0], "fromBlock": hex(frm), "toBlock": "latest"}]}])[0]
        res = o.get('result')
        print(chain, 'head', hex(head), 'from', hex(frm), 'logs', None if res is None else len(res), o.get('error'))
        if res:
            addrs = {}
            for l in res:
                addrs[l['address']] = addrs.get(l['address'], 0) + 1
            print(sorted(addrs.items(), key=lambda x: -x[1])[:6])
