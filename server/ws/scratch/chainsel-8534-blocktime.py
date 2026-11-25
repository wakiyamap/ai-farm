import json, sys, urllib.request
# usage: chainlist.json name-substring=chainId ...
cl = json.load(open(sys.argv[1]))
byid = {c['chainId']: c for c in cl}
def call(url, method, params):
    req = urllib.request.Request(url, data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode(),
                                 headers={"Content-Type": "application/json", "User-Agent": "farm-research/1"})
    with urllib.request.urlopen(req, timeout=8) as r:
        return json.load(r)['result']
for arg in sys.argv[2:]:
    label, cid = arg.split('=')
    c = byid.get(int(cid))
    if not c:
        print(f'{label}: chainId {cid} not in chainlist'); continue
    urls = [u for u in c.get('rpc', []) if u.startswith('https://') and '${' not in u]
    done = False
    for u in urls[:5]:
        try:
            head = int(call(u, 'eth_blockNumber', []), 16)
            n = 2000
            b1 = call(u, 'eth_getBlockByNumber', [hex(head), False])
            b0 = call(u, 'eth_getBlockByNumber', [hex(head - n), False])
            t1, t0 = int(b1['timestamp'], 16), int(b0['timestamp'], 16)
            gotid = int(call(u, 'eth_chainId', []), 16)
            print(f'{label} chainId={gotid} head={head} avg_block_s={(t1-t0)/n:.3f} over {n} blocks ({t0}->{t1}) via {u}')
            done = True; break
        except Exception as e:
            continue
    if not done:
        print(f'{label}: no public RPC answered ({len(urls)} candidates)')
