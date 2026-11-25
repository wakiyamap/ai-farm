#!/usr/bin/env python3
"""Run cdd0d3e7: burn census. Topic-only eth_getLogs Transfer(*, to=0x0) from ANY token, grouped by token;
then one receipt per mid-frequency token (its last burn tx): flag txs that also swap (burn + swap = NAV-arb shape).
usage: burncensus.py <chain> <blocks back> <page> [min_n] [max_n] [cap]"""
import json, os, sys, urllib.request, collections, time
RELAY = os.environ.get('RPC_RELAY_URL', 'http://127.0.0.1:8545').rstrip('/')
chain, back, page = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
lo_n = int(sys.argv[4]) if len(sys.argv) > 4 else 3
hi_n = int(sys.argv[5]) if len(sys.argv) > 5 else 2000
cap = int(sys.argv[6]) if len(sys.argv) > 6 else 120
T = '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
ZERO = '0x' + '0' * 64
SWAPS = {
 '0xd78ad95fa46c994b6551d0da85fc275fe613ce37657fb8d5e3d130840159d822': 'V2',
 '0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67': 'V3',
 '0x19b47279256b2a23a1665c810c8d55a1758940ee09377d4f8d26497a3577dc83': 'PcsV3',
 '0x40e9cecb9f5f1f1c5b9c97dec2917b7ee92e57ba5563708daca94dd84ad7112f': 'V4',
 '0xc2c0245e056d5fb095f04cd6373bc770802ebd1e6c918eb78fdef843cdb37b0f': 'DODO',
 '0x2170c741c41531aec20e7c107c24eecfdd15e69c9bb0a8dd37b1840b9e0b207b': 'BalV2',
 '0x8b3e96f2b889fa771c53c981b40daf005f63f637f1869f707052d15a3dd97140': 'Curve',
}
FLASH = {'0xc76f1b4fe4396ac07a9fa55a415d4ca430e72651d37d3401f3bed7cb13fc4f12', '0x0d7d75e01ab95780d3cd1c8ec0dd6c2ce19e3a20427eec8bf53283b6fb8e95f0',
         '0xefefaba5e921573100900a3ad9cf29f222d995fb3b6045797eaea7521bd8d6f0', '0x0b2e13ff20ac7b474198655583edf70dedd2c1dc980e329c4fbb2fc0748b796b'}
calls = 0


def rpc(method, params):
    global calls
    body = json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params}).encode()
    err = None
    for attempt in range(3):
        try:
            calls += 1
            req = urllib.request.Request(f'{RELAY}/{chain}?lane=research', body, {'content-type': 'application/json'})
            ans = json.load(urllib.request.urlopen(req, timeout=60))
            if 'error' in ans:
                raise RuntimeError(str(ans['error'])[:200])
            return ans['result']
        except Exception as e:
            err = e
            time.sleep(1 + attempt)
    raise err


head = int(rpc('eth_blockNumber', []), 16)
start = head - back
tok = collections.defaultdict(lambda: {'n': 0, 'txs': []})


def scan(a, b, depth=0):
    try:
        logs = rpc('eth_getLogs', [{'fromBlock': hex(a), 'toBlock': hex(b), 'topics': [T, None, ZERO]}])
    except Exception as e:
        if b > a and depth < 6:
            m = (a + b) // 2
            scan(a, m, depth + 1); scan(m + 1, b, depth + 1)
        else:
            print('ERRPAGE', a, b, str(e)[:80])
        return
    for l in logs:
        if len(l['topics']) != 3:
            continue  # NFTs
        t = tok[l['address']]
        t['n'] += 1
        if not t['txs'] or t['txs'][-1] != l['transactionHash']:
            t['txs'].append(l['transactionHash'])


a = start
while a <= head:
    b = min(a + page - 1, head)
    scan(a, b)
    a = b + 1
print(chain, 'head', head, 'from', start, 'tokens', len(tok), 'burn logs', sum(t['n'] for t in tok.values()), 'calls', calls)
json.dump({'chain': chain, 'head': head, 'from': start, 'tokens': {k: {'n': v['n'], 'ntx': len(v['txs']), 'txs': v['txs'][-5:]} for k, v in tok.items()}},
          open(f'/srv/farm/ws/scratch/rca23/burns-{chain}.json', 'w'))
cands = sorted([(k, v) for k, v in tok.items() if lo_n <= len(v['txs']) <= hi_n], key=lambda kv: -len(kv[1]['txs']))
out = []
for k, v in cands[:cap]:
    tx = v['txs'][-1]
    try:
        rc = rpc('eth_getTransactionReceipt', [tx])
    except Exception as e:
        print('ERR', k, str(e)[:80]); continue
    if not rc:
        continue
    sw = collections.Counter(); fl = 0; mints = set(); burns = set()
    for l in rc['logs']:
        t0 = l['topics'][0] if l['topics'] else ''
        if t0 in SWAPS: sw[SWAPS[t0]] += 1
        if t0 in FLASH: fl += 1
        if t0 == T and len(l['topics']) == 3:
            if l['topics'][1] == ZERO: mints.add(l['address'])
            if l['topics'][2] == ZERO: burns.add(l['address'])
    row = {'token': k, 'ntx': len(v['txs']), 'n': v['n'], 'tx': tx, 'from': rc['from'], 'to': rc['to'], 'idx': int(rc['transactionIndex'], 16),
           'gas': int(rc['gasUsed'], 16), 'swaps': dict(sw), 'flash': fl, 'mints': sorted(mints), 'burns': sorted(burns), 'nlogs': len(rc['logs'])}
    out.append(row)
    if sw:
        print('SW', k, 'ntx', row['ntx'], 'to', rc['to'], 'from', rc['from'][:12], 'idx', row['idx'], 'gas', row['gas'], dict(sw), 'fl', fl, 'b', len(burns), 'm', len(mints), tx)
json.dump(out, open(f'/srv/farm/ws/scratch/rca23/classified-{chain}.json', 'w'), indent=0)
print('classified', len(out), 'with swaps', sum(1 for r in out if r['swaps']), 'calls', calls)
