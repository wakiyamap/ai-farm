import json, subprocess, urllib.request, sys, time

FORK = 'http://127.0.0.1:9001'
SEL = json.load(open('/srv/farm/ws/scratch/mb157-sel.json'))
# add two burst-block captures (same-block burst markets)
extra_blocks = {55675686, 55691524}
rows_all = [json.loads(l) for l in open('/srv/farm/ws/scratch/mb157-caps.json') if l.strip()]
rows_all = [r for r in rows_all if '_note' not in r]
for r in rows_all:
    if r['block'] in extra_blocks and all(s['block'] != r['block'] for s in SEL):
        SEL.append(r)
ETH_USD = 2050.0  # gate-derived, attempts 969
LADDER_LO = 1  # trace proves round visible at C-1
LOOK = 4096

def rpc(m, p):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": m, "params": p}).encode()
    req = urllib.request.Request(FORK, body, {'content-type': 'application/json'})
    return json.loads(urllib.request.urlopen(req, timeout=60).read())

def walk_find(c, depth, best):
    # deepest latestRoundData callee
    if c.get('input', '')[2:10] == 'feaf968c':
        if depth >= best[0]:
            best[:] = [depth, c['to'], c.get('output', '')]
    for ch in c.get('calls', []):
        walk_find(ch, depth + 1, best)

def word0(out):
    return int(out[2:66], 16) if len(out) >= 66 else None

out_rows = []
groups = {}
for r in SEL:
    C, tx = r['block'], r['tx_hash']
    tf = f'/srv/farm/ws/scratch/mb157-tr-{C}.json'
    p = subprocess.run(['fork', 'trace', 'base', tx], capture_output=True, text=True)
    s = p.stdout
    try:
        d = json.loads(s[s.find('{'):])
    except Exception:
        out_rows.append({'block': C, 'error': 'trace fail ' + s[:120]})
        continue
    json.dump(d, open(tf, 'w'))
    best = [-1, None, '']
    walk_find(d, 0, best)
    depth, feed, output = best
    if not feed:
        out_rows.append({'block': C, 'error': 'no latestRoundData'})
        continue
    subprocess.run(['fork', 'reset', 'base', str(C - 1)], capture_output=True, text=True)
    hdrC = rpc('eth_getBlockByNumber', ['latest', False])['result']
    tsC = int(hdrC['timestamp'], 16)
    tsC_block = int(hdrC['number'], 16)
    R = word0(output)
    gasUsed = int(d.get('gasUsed', '0'), 16)
    key = (feed, R)
    groups.setdefault(key, [])
    groups[key].append(C)
    out_rows.append({'block': C, 'tx': tx, 'repaid_usd': round(int(r['ra']) / 1e6, 2),
                     'feed': feed, 'round_C': hex(R), 'gasUsed': gasUsed, 'tsC': tsC})
    print('traced', C, 'feed', feed[:12], 'round', hex(R), flush=True)

# binary search publish block Pb per (feed, round)
pub = {}
for (feed, R), Cs in groups.items():
    Cmin = min(Cs)
    lo, hi = Cmin - LOOK, Cmin - 1  # round visible at Cmin-1 (trace)
    Pb = None
    probes = 0
    # verify hi shows R
    while lo < hi:
        mid = (lo + hi + 1) // 2
        subprocess.run(['fork', 'reset', 'base', str(mid)], capture_output=True, text=True)
        j = rpc('eth_call', [{'from': '0x000000000000000000000000000000000000f00d', 'to': feed,
                              'data': '0xfeaf968c'}, 'latest'])
        probes += 1
        ok = False
        if 'result' in j:
            ok = word0(j['result']) == R
        else:
            print('probe error at tag', mid, json.dumps(j.get('error', ''))[:150], flush=True)
        if ok:
            hi = mid  # visible at tag mid -> Pb <= mid
        else:
            lo = mid + 1  # not visible at tag mid -> Pb > mid
        if probes > 16:
            break
    # invariant: at tag lo-1? check lo shows R (converged)
    subprocess.run(['fork', 'reset', 'base', str(lo)], capture_output=True, text=True)
    j = rpc('eth_call', [{'from': '0x000000000000000000000000000000000000f00d', 'to': feed,
                          'data': '0xfeaf968c'}, 'latest'])
    Pb = lo if ('result' in j and word0(j['result']) == R) else None
    # header at tag lo (== Pb when found): baseFee + timestamp of the publish block
    hdr = rpc('eth_getBlockByNumber', ['latest', False])['result']
    pub[(feed, R)] = {'Pb': Pb, 'probes': probes, 'lo': lo, 'ts_lo': int(hdr['timestamp'], 16),
                      'baseFee': int(hdr['baseFeePerGas'], 16)}
    print('pub', feed[:12], hex(R), 'Pb', Pb, 'probes', probes, 'baseFee', pub[(feed, R)]['baseFee'], flush=True)

# finalize per capture
tsC_by_block = {r['block']: r.get('tsC') for r in out_rows}
final = []
for row in out_rows:
    if 'error' in row:
        final.append(row); continue
    key = (row['feed'], int(row['round_C'], 16))
    g = pub.get(key)
    C = row['block']
    if not g or g['Pb'] is None:
        row['error'] = 'probe failed'; final.append(row); continue
    Pb = g['Pb']
    k = C - Pb
    secs = row.get('tsC') - g['ts_lo'] if row.get('tsC') is not None and g['Pb'] is not None else None
    bonus = 0.04384 * row['repaid_usd']
    gas_usd = row['gasUsed'] * g['baseFee'] / 1e18 * ETH_USD
    row.update({'Pb': Pb, 'window_blocks': k, 'window_seconds': secs,
                'race': k <= 2, 'bonus_usd': round(bonus, 2), 'gas_usd': round(gas_usd, 2),
                'net_usd': round(bonus - gas_usd, 2)})
    final.append(row)
    print(json.dumps(row), flush=True)

json.dump(final, open('/srv/farm/ws/scratch/mb157-window.json', 'w'), indent=1)
print('done')
