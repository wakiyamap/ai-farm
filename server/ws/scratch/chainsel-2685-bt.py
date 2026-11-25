import json, sys, urllib.request
def call(url, m, p):
    req = urllib.request.Request(url, data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": m, "params": p}).encode(),
                                 headers={"Content-Type": "application/json", "User-Agent": "farm-research/1"})
    return json.load(urllib.request.urlopen(req, timeout=10))['result']
for u in sys.argv[1:]:
    try:
        cid = int(call(u, 'eth_chainId', []), 16); h = int(call(u, 'eth_blockNumber', []), 16)
        t1 = int(call(u, 'eth_getBlockByNumber', [hex(h), False])['timestamp'], 16)
        t0 = int(call(u, 'eth_getBlockByNumber', [hex(h - 2000), False])['timestamp'], 16)
        print(u, 'chainId', cid, 'head', h, 'avg_block_s %.3f' % ((t1 - t0) / 2000))
    except Exception as e:
        print(u, 'fail', str(e)[:80])
