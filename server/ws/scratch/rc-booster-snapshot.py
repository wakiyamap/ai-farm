"""Snapshot all Booster pools: poolInfo, and claimable CRV for the voter proxy on active ones.
usage: rc-booster-snapshot.py <chain> <booster> <voterproxy> <out.json> [from_pid]
Read-only (research lane eth_call)."""
import json, os, sys, urllib.request
chain, booster, proxy, out = sys.argv[1], sys.argv[2], sys.argv[3].lower(), sys.argv[4]
start = int(sys.argv[5]) if len(sys.argv) > 5 else 0
url = os.environ['RPC_RELAY_URL'].rstrip('/') + '/' + chain + '?lane=research'
def call(to, data):
    body = json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': 'eth_call', 'params': [{'to': to, 'data': data}, 'latest']}).encode()
    r = urllib.request.Request(url, data=body, headers={'content-type': 'application/json'})
    j = json.loads(urllib.request.urlopen(r, timeout=30).read())
    return j.get('result'), j.get('error')
n = int(call(booster, '0x081e3eda')[0], 16)
rows = []
for pid in range(start, n):
    res, err = call(booster, '0x1526fe27' + format(pid, '064x'))
    if not res or len(res) < 2 + 64 * 6:
        rows.append({'pid': pid, 'err': str(err)}); continue
    w = [res[2 + 64 * i: 2 + 64 * (i + 1)] for i in range(6)]
    gauge = '0x' + w[2][-40:]; crvr = '0x' + w[3][-40:]; shut = int(w[5], 16) != 0
    row = {'pid': pid, 'lp': '0x' + w[0][-40:], 'gauge': gauge, 'crvRewards': crvr, 'shutdown': shut}
    if not shut:
        c, e = call(gauge, '0x33134583' + '0' * 24 + proxy[2:])
        row['claimable'] = int(c, 16) / 1e18 if c and len(c) >= 66 else None
        if e: row['claim_err'] = str(e)[:120]
    rows.append(row)
json.dump(rows, open(out, 'w'))
act = [r for r in rows if r.get('claimable')]
act.sort(key=lambda r: -r['claimable'])
print('pools', n, 'active', sum(1 for r in rows if r.get('shutdown') is False), 'with claimable', len(act),
      'sum claimable', round(sum(r['claimable'] for r in act), 1))
for r in act[:25]:
    print(r['pid'], r['gauge'], r['crvRewards'], round(r['claimable'], 1))
