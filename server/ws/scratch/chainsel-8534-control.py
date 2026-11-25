import json, sys, urllib.request, collections
url, addr, n = sys.argv[1], sys.argv[2], int(sys.argv[3])
def call(m, p):
    req = urllib.request.Request(url, data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": m, "params": p}).encode(),
                                 headers={"Content-Type": "application/json", "User-Agent": "farm-research/1"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)['result']
head = int(call('eth_blockNumber', []), 16)
logs = call('eth_getLogs', [{"address": addr, "fromBlock": hex(head - n), "toBlock": hex(head)}])
c = collections.Counter(l['topics'][0] for l in logs)
print('blocks', head - n, head, 'logs', len(logs))
for k, v in c.most_common(8): print(k, v)
