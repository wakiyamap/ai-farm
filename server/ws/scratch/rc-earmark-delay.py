"""For each lump earmark (caller share >= min_crv): delay from crvRewards.periodFinish (read at b-1) to inclusion,
winner sender, priority fee paid. usage: rc-earmark-delay.py <chain> logs.json bps min_crv out.json"""
import json, os, sys, urllib.request, collections
chain, path, bps, mn, outp = sys.argv[1], sys.argv[2], int(sys.argv[3]), float(sys.argv[4]), sys.argv[5]
url = os.environ['RPC_RELAY_URL'].rstrip('/') + '/' + chain + '?lane=research'
def rpc(m, p):
    body = json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': m, 'params': p}).encode()
    r = urllib.request.Request(url, data=body, headers={'content-type': 'application/json'})
    j = json.loads(urllib.request.urlopen(r, timeout=30).read())
    return j.get('result')
stakers = {'0x3fe65692bfcd0e6cf84cb1e7d24108e434a7587e', '0xcf50b810e57ac33b91dcf525c6ddd9881b139332',
           '0x1389388d01708118b497f59521f6943be2541bb7'}
logs = json.load(open(path))
bytx = collections.defaultdict(list)
for l in logs:
    bytx[l['transactionHash']].append(('0x' + l['topics'][2][-40:], int(l['data'], 16) / 1e18, int(l['blockNumber'], 16)))
res = []
for tx, rows in bytx.items():
    tot = sum(a for _, a, _ in rows); exp = tot * bps / 10000
    agg = collections.defaultdict(float)
    for r, a, _ in rows: agg[r] += a
    caller = min(agg.items(), key=lambda kv: abs(kv[1] - exp))
    if caller[1] < mn: continue
    b = rows[0][2]
    pools = [r for r, a in agg.items() if r not in stakers and a > tot * 0.05 and r != caller[0]]
    pool = max(pools, key=lambda r: agg[r]) if pools else None
    pf = rpc('eth_call', [{'to': pool, 'data': '0xebe2b12b'}, hex(b - 1)]) if pool else None
    blk = rpc('eth_getBlockByNumber', [hex(b), False])
    t = rpc('eth_getTransactionByHash', [tx]); rc = rpc('eth_getTransactionReceipt', [tx])
    ts = int(blk['timestamp'], 16); base = int(blk['baseFeePerGas'], 16)
    egp = int(rc['effectiveGasPrice'], 16) if rc else None
    pfv = int(pf, 16) if pf and len(pf) >= 66 else None
    idx = int(t['transactionIndex'], 16)
    row = {'tx': tx, 'block': b, 'ts': ts, 'pool': pool, 'periodFinish': pfv, 'delay_s': ts - pfv if pfv else None,
           'caller_contract': caller[0], 'from': t['from'], 'to': t['to'], 'caller_crv': round(caller[1], 2),
           'gasUsed': int(rc['gasUsed'], 16) if rc else None, 'prio_gwei': (egp - base) / 1e9 if egp else None,
           'base_gwei': base / 1e9, 'tx_index': idx}
    res.append(row)
    print(json.dumps(row))
json.dump(res, open(outp, 'w'))
