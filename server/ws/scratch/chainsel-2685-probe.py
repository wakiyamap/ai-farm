import json, urllib.request, sys
url = sys.argv[1]
def raw(body):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json", "User-Agent": "farm-research/1"})
    return json.load(urllib.request.urlopen(req, timeout=30))
h = int(raw({"jsonrpc": "2.0", "id": 1, "method": "eth_blockNumber", "params": []})['result'], 16)
print('head', h)
print('archive', raw({"jsonrpc": "2.0", "id": 1, "method": "eth_call", "params": [{"to": sys.argv[2], "data": "0x2c3c9157" + "00" * 32}, hex(int(sys.argv[3]))]}))
print('batch', str(raw([{"jsonrpc": "2.0", "id": i, "method": "eth_blockNumber", "params": []} for i in range(3)]))[:300])
