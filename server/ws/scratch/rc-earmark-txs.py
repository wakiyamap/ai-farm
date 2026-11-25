"""For sampled earmark txs: tx.from, gasUsed, effectiveGasPrice, caller CRV received.
usage: rc-earmark-txs.py <chain> logs.json <n_per_recipient> <recipient...>"""
import json, os, sys, urllib.request, collections
chain, path, n = sys.argv[1], sys.argv[2], int(sys.argv[3])
wanted = [a.lower() for a in sys.argv[4:]]
url = os.environ['RPC_RELAY_URL'].rstrip('/') + '/' + chain + '?lane=research'
def rpc(m, p):
    body = json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': m, 'params': p}).encode()
    r = urllib.request.Request(url, data=body, headers={'content-type': 'application/json'})
    return json.loads(urllib.request.urlopen(r, timeout=30).read())['result']
logs = json.load(open(path))
bytx = collections.defaultdict(list)
for l in logs:
    bytx[l['transactionHash']].append(('0x' + l['topics'][2][-40:], int(l['data'], 16) / 1e18))
seen = collections.Counter()
for tx, rows in sorted(bytx.items(), key=lambda kv: kv[0]):
    rec = {r for r, _ in rows}
    for w in wanted:
        if w in rec and seen[w] < n:
            seen[w] += 1
            t = rpc('eth_getTransactionByHash', [tx])
            rc = rpc('eth_getTransactionReceipt', [tx])
            got = sum(a for r, a in rows if r == w)
            gu = int(rc['gasUsed'], 16) if rc else None
            gp = int(rc['effectiveGasPrice'], 16) if rc else int(t.get('gasPrice', '0x0'), 16)
            print(json.dumps({'tx': tx, 'block': int(t['blockNumber'], 16), 'from': t['from'], 'to': t['to'],
                              'sel': t['input'][:10], 'recipient': w, 'crv_to_recipient': round(got, 4),
                              'n_logs': len(rows), 'gasUsed': gu, 'gwei': gp / 1e9 if gp else None,
                              'fee_eth': (gu * gp / 1e18) if gu else None}))
