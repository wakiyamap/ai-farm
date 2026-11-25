import json, sys, urllib.request, collections, time
# usage: rpc_url pool oracle days blocktime_s chunk out.json
url, pool, oracle = sys.argv[1], sys.argv[2], sys.argv[3]
days, bt, chunk, out = float(sys.argv[4]), float(sys.argv[5]), int(sys.argv[6]), sys.argv[7]
T0 = '0xe413a321e8681d831f4dbccbca790d2952b56f977908e45be37335533e005286'
def call(method, params, tries=4):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode(),
                                         headers={"Content-Type": "application/json", "User-Agent": "farm-research/1"})
            with urllib.request.urlopen(req, timeout=20) as r:
                j = json.load(r)
            if 'error' in j: raise RuntimeError(j['error'])
            return j['result']
        except Exception as e:
            err = e; time.sleep(1 + i)
    raise err
head = int(call('eth_blockNumber', []), 16)
start = head - int(days * 86400 / bt)
logs = []; b = start; calls = 0
while b <= head:
    e = min(b + chunk - 1, head)
    logs += call('eth_getLogs', [{"address": pool, "topics": [T0], "fromBlock": hex(b), "toBlock": hex(e)}]); calls += 1
    b = e + 1
tsa = int(call('eth_getBlockByNumber', [hex(start), False])['timestamp'], 16)
tsb = int(call('eth_getBlockByNumber', [hex(head), False])['timestamp'], 16)
# prices (8 dec USD) and decimals per debt asset
dec = {}; px = {}
for l in logs:
    a = '0x' + l['topics'][2][-40:]
    if a not in dec:
        dec[a] = int(call('eth_call', [{"to": a, "data": "0x313ce567"}, "latest"]), 16)
        px[a] = int(call('eth_call', [{"to": oracle, "data": "0xb3596f07" + a[2:].rjust(64, '0')}, "latest"]), 16) / 1e8
by = collections.defaultdict(lambda: [0, 0.0]); tot = 0.0; big = 0
for l in logs:
    a = '0x' + l['topics'][2][-40:]
    d = l['data'][2:]
    debt = int(d[0:64], 16) / 10 ** dec[a] * px[a]
    liq = '0x' + d[128 + 24:192]
    by[liq][0] += 1; by[liq][1] += debt; tot += debt
    if debt >= 1000: big += 1
res = {"rpc": url, "pool": pool, "from_block": start, "to_block": head, "from_ts": tsa, "to_ts": tsb, "days": (tsb - tsa) / 86400,
       "getLogs_calls": calls, "events": len(logs), "repaid_usd_at_head_prices": round(tot), "events_ge_1k_usd": big,
       "liquidators": sorted([[k, v[0], round(v[1])] for k, v in by.items()], key=lambda x: -x[1])[:10]}
json.dump(res, open(out, 'w'), indent=1)
print(json.dumps(res, indent=1))
