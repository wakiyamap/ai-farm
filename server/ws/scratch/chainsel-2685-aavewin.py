"""Aave V3 LiquidationCall 30 d scan + per-capture takeable window (first block of the HF<1 run ending at the capture).
usage: rpc pool oracle days chunk out.json [max_events_for_windows]
Window: HF (getUserAccountData word 5) at B-1; if <1, exponential back-off then bisection to the first block of the HF<1 run.
Window seconds = ts(B) - ts(first HF<1 block). 0 = healthy at B-1 (crossed inside the capture block).
Gross = collateral seized x price - debt covered x price, at the Aave oracle at HEAD (approximation)."""
import json, sys, urllib.request, collections, time, random
url, pool, oracle = sys.argv[1], sys.argv[2], sys.argv[3]
days, chunk, out = float(sys.argv[4]), int(sys.argv[5]), sys.argv[6]
maxw = int(sys.argv[7]) if len(sys.argv) > 7 else 10 ** 9
T0 = '0xe413a321e8681d831f4dbccbca790d2952b56f977908e45be37335533e005286'
ncalls = 0
def call(method, params, tries=5):
    global ncalls
    for i in range(tries):
        try:
            ncalls += 1
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
tsh = int(call('eth_getBlockByNumber', [hex(head), False])['timestamp'], 16)
# estimate start block from a sample
b2 = head - 200000; ts2 = int(call('eth_getBlockByNumber', [hex(b2), False])['timestamp'], 16)
bt = (tsh - ts2) / 200000
start = head - int(days * 86400 / bt)
logs = []; b = start
while b <= head:
    e = min(b + chunk - 1, head)
    logs += call('eth_getLogs', [{"address": pool, "topics": [T0], "fromBlock": hex(b), "toBlock": hex(e)}])
    b = e + 1
    if (b - start) // chunk % 50 == 0: print('scan', b, len(logs), flush=True)
tsa = int(call('eth_getBlockByNumber', [hex(start), False])['timestamp'], 16)
dec = {}; px = {}
def meta(a):
    if a not in dec:
        dec[a] = int(call('eth_call', [{"to": a, "data": "0x313ce567"}, "latest"]), 16)
        px[a] = int(call('eth_call', [{"to": oracle, "data": "0xb3596f07" + a[2:].rjust(64, '0')}, "latest"]), 16) / 1e8
ev = []
for l in logs:
    col = '0x' + l['topics'][1][-40:]; debt = '0x' + l['topics'][2][-40:]; user = '0x' + l['topics'][3][-40:]
    meta(col); meta(debt)
    d = l['data'][2:]
    dv = int(d[0:64], 16) / 10 ** dec[debt] * px[debt]; cv = int(d[64:128], 16) / 10 ** dec[col] * px[col]
    ev.append({"block": int(l['blockNumber'], 16), "tx": l['transactionHash'], "user": user, "liquidator": '0x' + d[128 + 24:192],
               "debt_usd": round(dv, 2), "gross_usd": round(cv - dv, 2)})
def hf(user, blk):
    r = call('eth_call', [{"to": pool, "data": "0xbf92857c" + user[2:].rjust(64, '0')}, hex(blk)])
    return int(r[2 + 5 * 64:2 + 6 * 64], 16) / 1e18
tscache = {}
def ts(blk):
    if blk not in tscache: tscache[blk] = int(call('eth_getBlockByNumber', [hex(blk), False])['timestamp'], 16)
    return tscache[blk]
idx = list(range(len(ev)))
random.seed(7)
if len(idx) > maxw: idx = sorted(random.sample(idx, maxw))
for i in idx:
    x = ev[i]; B = x['block']
    try:
        if hf(x['user'], B - 1) >= 1:
            x['win_blocks'] = 0; x['win_s'] = 0; continue
        lo = 1; step = 1; capped = False
        while True:
            step *= 4
            if step > 2_000_000: capped = True; break
            if hf(x['user'], B - step) >= 1: break
            lo = step
        if capped:
            x['win_blocks'] = lo; x['win_s'] = ts(B) - ts(B - lo); x['capped'] = True; continue
        hi = step  # HF>=1 at B-hi, <1 at B-lo
        while hi - lo > 1:
            m = (lo + hi) // 2
            if hf(x['user'], B - m) < 1: lo = m
            else: hi = m
        x['win_blocks'] = lo; x['win_s'] = ts(B) - ts(B - lo)
    except Exception as e:
        x['win_err'] = str(e)[:80]
    print('win', B, x.get('win_blocks'), x.get('win_s'), x['gross_usd'], flush=True)
by = collections.Counter(x['liquidator'] for x in ev)
measured = [x for x in ev if 'win_s' in x]
ok = [x for x in measured if x['win_s'] >= 3]
res = {"rpc": url, "pool": pool, "from_block": start, "to_block": head, "days": (tsh - tsa) / 86400, "avg_block_s": bt,
       "events": len(ev), "repaid_usd_at_head": round(sum(x['debt_usd'] for x in ev)), "gross_usd_at_head": round(sum(x['gross_usd'] for x in ev)),
       "top_liquidators": by.most_common(5), "distinct_liquidators": len(by),
       "windows_measured": len(measured), "windows_ge_3s": len(ok), "gross_ge_3s_usd": round(sum(x['gross_usd'] for x in ok), 2),
       "rpc_calls": ncalls, "events_detail": ev}
json.dump(res, open(out, 'w'), indent=1)
print(json.dumps({k: v for k, v in res.items() if k != 'events_detail'}, indent=1))
