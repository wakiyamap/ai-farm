import json, urllib.request, sys
url, to = sys.argv[1], sys.argv[2]
def raw(body):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json", "User-Agent": "farm-research/1"})
    return json.load(urllib.request.urlopen(req, timeout=30))
h = int(raw({"jsonrpc": "2.0", "id": 1, "method": "eth_blockNumber", "params": []})['result'], 16)
for d in [100, 1000, 10000, 50000, 200000, 1000000, 5000000]:
    r = raw({"jsonrpc": "2.0", "id": 1, "method": "eth_getBalance", "params": [to, hex(h - d)]})
    print(d, 'ok' if 'result' in r else r['error']['message'][:60])
