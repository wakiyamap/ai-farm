import json, sys, urllib.request, collections, time
# usage: rpc morpho days blocktime chunk out
url, morpho = sys.argv[1], sys.argv[2]
days, bt, chunk, out = float(sys.argv[3]), float(sys.argv[4]), int(sys.argv[5]), sys.argv[6]
T0 = '0xa4946ede45d0c6f06a0f5ce92c9ad3b4751452d2fe0e25010783bcab57a67e41'
def call(m, p, tries=4):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": m, "params": p}).encode(),
                                         headers={"Content-Type": "application/json", "User-Agent": "farm-research/1"})
            with urllib.request.urlopen(req, timeout=30) as r:
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
    logs += call('eth_getLogs', [{"address": morpho, "topics": [T0], "fromBlock": hex(b), "toBlock": hex(e)}]); calls += 1
    b = e + 1
tsa = int(call('eth_getBlockByNumber', [hex(start), False])['timestamp'], 16)
tsb = int(call('eth_getBlockByNumber', [hex(head), False])['timestamp'], 16)
loan = {}; dec = {}; sym = {}
by = collections.defaultdict(lambda: [0, 0.0]); per_token = collections.defaultdict(float)
for l in logs:
    mid = l['topics'][1]
    if mid not in loan:
        r = call('eth_call', [{"to": morpho, "data": "0x2c3c9157" + mid[2:]}, "latest"])
        loan[mid] = '0x' + r[2 + 24:2 + 64]
    t = loan[mid]
    if t not in dec:
        dec[t] = int(call('eth_call', [{"to": t, "data": "0x313ce567"}, "latest"]), 16)
        try:
            rs = call('eth_call', [{"to": t, "data": "0x95d89b41"}, "latest"])
            ln = int(rs[2 + 64:2 + 128], 16); sym[t] = bytes.fromhex(rs[2 + 128:2 + 128 + 2 * ln]).decode(errors='replace')
        except Exception:
            sym[t] = t
    amt = int(l['data'][2:66], 16) / 10 ** dec[t]
    caller = '0x' + l['topics'][2][-40:]
    by[caller][0] += 1; per_token[sym[t]] += amt
res = {"rpc": url, "morpho": morpho, "from_block": start, "to_block": head, "days": (tsb - tsa) / 86400, "getLogs_calls": calls,
       "events": len(logs), "repaid_by_loan_token_units": {k: round(v, 2) for k, v in per_token.items()},
       "callers": sorted([[k, v[0]] for k, v in by.items()], key=lambda x: -x[1])[:8], "distinct_callers": len(by)}
json.dump(res, open(out, 'w'), indent=1)
print(json.dumps(res, indent=1))
