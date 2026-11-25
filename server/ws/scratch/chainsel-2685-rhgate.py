import json, urllib.request, collections
url = "https://rpc.mainnet.chain.robinhood.com"
A = '0x2bd3d5965b26b51814ac95127b2b80dd6ccc0fa1'
def call(m, p):
    req = urllib.request.Request(url, data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": m, "params": p}).encode(),
                                 headers={"Content-Type": "application/json", "User-Agent": "farm-research/1"})
    j = json.load(urllib.request.urlopen(req, timeout=30))
    return j.get('result', j.get('error'))
print('code bytes', (len(call('eth_getCode', [A, 'latest'])) - 2) // 2)
rc = call('eth_getTransactionReceipt', ['0x1dd17482bafb1d9783a0ff049d2732bc604cff64e32ce15d57fa1829f47984f2'])
l0 = rc['logs'][0]
print('log0 topics', l0['topics'], 'data', l0['data'][:400])
h = int(call('eth_blockNumber', []), 16)
lg = call('eth_getLogs', [{"address": A, "fromBlock": hex(h - 99999), "toBlock": hex(h)}])
print('logs last 100k blocks', len(lg) if isinstance(lg, list) else lg)
if isinstance(lg, list):
    print(collections.Counter(l['topics'][0][:10] for l in lg).most_common(5))
# EIP-1967 implementation slot
impl = call('eth_getStorageAt', [A, '0x360894a13ba1a3210667c828492db98dca3e2076cc3735a9e7ca5ac7c1fb7a6c', 'latest'])
print('impl slot', impl)
# common names
for sig, sel in [('name()', '0x06fdde03'), ('owner()', '0x8da5cb5b'), ('MORPHO()', '0x3acb5624')]:
    print(sig, call('eth_call', [{"to": A, "data": sel}, 'latest']))
