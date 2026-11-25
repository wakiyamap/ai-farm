"""Stage 2: per-capture window on Robinhood Chain Morpho = ts(capture block) - ts(last oracle feed update at or before the capture block).
Feed update = AnswerUpdated on the market's feed proxies/aggregators (fallback: any log of those addresses).
0 = an update landed in the capture block itself (crossing inside the capture block).
Gross proxy = repaid x (LIF - 1), LIF = min(1.15, 1/(1 - 0.3 (1 - lltv))) (Morpho Blue formula), USDG loans only (USDG ~ 1 USD)."""
import json, urllib.request, time, collections
url = "https://rpc.mainnet.chain.robinhood.com"
AU = '0x0559884fd3a460db3073b7fc896cc77986f16e378210ded43186175bf646fc5f'
d = json.load(open('chainsel-2685-rh-events.json'))
ev, mk = d['events'], d['markets']
def call(m, p, tries=4):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": m, "params": p}).encode(),
                                         headers={"Content-Type": "application/json", "User-Agent": "farm-research/1"})
            j = json.load(urllib.request.urlopen(req, timeout=30))
            if 'error' in j: raise RuntimeError(j['error'])
            return j['result']
        except Exception as e:
            err = e; time.sleep(1 + i)
    raise err
tsc = {}
def ts(b):
    if b not in tsc: tsc[b] = int(call('eth_getBlockByNumber', [hex(b), False])['timestamp'], 16)
    return tsc[b]
out = []
for x in ev:
    m = mk[x['id']]
    addrs = sorted(set(a for f in m['feeds'].values() for a in (f['feed'], f['aggregator']) if a))
    B = x['block']; last = None; how = None
    if addrs:
        for span in (3000, 30000, 99999):
            lg = call('eth_getLogs', [{"address": addrs, "topics": [AU], "fromBlock": hex(B - span), "toBlock": hex(B)}])
            if lg:
                last = max(int(l['blockNumber'], 16) for l in lg if int(l['blockNumber'], 16) < B or int(l['transactionIndex'], 16) < x['txi']) if any(int(l['blockNumber'], 16) < B or int(l['transactionIndex'], 16) < x['txi'] for l in lg) else None
                if last: how = 'AnswerUpdated'; break
    if last is None:
        lg = call('eth_getLogs', [{"address": addrs + [m['oracle']], "fromBlock": hex(B - 30000), "toBlock": hex(B)}])
        prior = [int(l['blockNumber'], 16) for l in lg if int(l['blockNumber'], 16) < B or int(l['transactionIndex'], 16) < x['txi']]
        if prior: last = max(prior); how = 'anylog'
    feedtype = ','.join(sorted(set((f['desc'] or '?') for f in m['feeds'].values()))) or 'non-ChainlinkOracleV2'
    lltv = m['lltv']; lif = min(1.15, 1 / (1 - 0.3 * (1 - lltv)))
    loan_sym, loan_dec = m['syms'][m['loan']]
    rep = x['repaid'] / 10 ** loan_dec
    gross = rep * (lif - 1) if m['loan'] == '0x5fc5360d0400a0fd4f2af552add042d716f1d168' else None
    w = (ts(B) - ts(last)) if last is not None else None
    r = {"block": B, "tx": x['tx'], "caller": x['caller'], "market": m['syms'][m['coll']][0] + '/' + loan_sym, "repaid": round(rep, 2), "feeds": feedtype,
         "gross_usd": round(gross, 2) if gross is not None else None, "last_update_block": last, "how": how,
         "win_blocks": (B - last) if last is not None else None, "win_s": w}
    out.append(r); print(json.dumps(r), flush=True)
cnt = collections.Counter('none' if r['win_s'] is None else ('0' if r['win_blocks'] == 0 else ('<3s' if r['win_s'] < 3 else '>=3s')) for r in out)
ok = [r for r in out if r['win_s'] is not None and r['win_s'] >= 3 and r['gross_usd']]
summ = {"events": len(out), "classes": cnt, "ge3s_n": len(ok), "ge3s_gross_usd": round(sum(r['gross_usd'] for r in ok), 2),
        "all_gross_usd": round(sum(r['gross_usd'] or 0 for r in out), 2)}
json.dump({"summary": summ, "rows": out}, open('chainsel-2685-rh-windows.json', 'w'), indent=1)
print(json.dumps(summ))
