"""Stage 1: Robinhood Chain Morpho Liquidate events (30 d) + market params + oracle feeds."""
import json, urllib.request, sys, time, collections
url = "https://rpc.mainnet.chain.robinhood.com"
MORPHO = "0x9D53d5E3bd5E8d4Cbfa6DB1ca238AEA02E651010"
T0 = '0xa4946ede45d0c6f06a0f5ce92c9ad3b4751452d2fe0e25010783bcab57a67e41'
FROM, TO = 88285349, 112971063
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
def tryc(to, data):
    try:
        r = call('eth_call', [{"to": to, "data": data}, "latest"], tries=1)
        return r if r and r != '0x' else None
    except Exception:
        return None
logs = []; b = FROM
while b <= TO:
    e = min(b + 499999, TO)
    logs += call('eth_getLogs', [{"address": MORPHO, "topics": [T0], "fromBlock": hex(b), "toBlock": hex(e)}]); b = e + 1
    print("logs", b, len(logs), flush=True)
ev = []
for l in logs:
    d = l['data'][2:]; w = [int(d[i:i + 64], 16) for i in range(0, len(d), 64)]
    ev.append({"block": int(l['blockNumber'], 16), "tx": l['transactionHash'], "txi": int(l['transactionIndex'], 16), "id": l['topics'][1],
               "caller": '0x' + l['topics'][2][-40:], "borrower": '0x' + l['topics'][3][-40:],
               "repaid": w[0], "seized": w[2], "baddebt": w[3]})
json.dump({"events": ev}, open('chainsel-2685-rh-events.json', 'w'))
print('events saved', len(ev), flush=True)
mk = {}
for mid in sorted(set(x['id'] for x in ev)):
    r = call('eth_call', [{"to": MORPHO, "data": "0x2c3c9157" + mid[2:]}, "latest"])[2:]
    loan, coll, orc = ['0x' + r[i * 64 + 24:(i + 1) * 64] for i in range(3)]; lltv = int(r[256:320], 16)
    feeds = {}
    for name, sel in [("BASE_FEED_1", "0xf50a4718"), ("BASE_FEED_2", "0xdc53858c"), ("QUOTE_FEED_1", "0x56095e11"), ("QUOTE_FEED_2", "0xacfbd39e")]:
        r2 = tryc(orc, sel)
        if r2 and int(r2, 16):
            f = '0x' + r2[-40:]; agg = tryc(f, "0x245a7bfc"); ds = tryc(f, "0x7284e416")
            desc = None
            if ds:
                try:
                    ln = int(ds[66:130], 16); desc = bytes.fromhex(ds[130:130 + 2 * ln]).decode(errors='replace')
                except Exception: pass
            feeds[name] = {"feed": f, "aggregator": ('0x' + agg[-40:]) if agg else None, "desc": desc}
    syms = {}
    for t in (loan, coll):
        rs = tryc(t, "0x95d89b41"); dc = tryc(t, "0x313ce567")
        try:
            ln = int(rs[66:130], 16); s = bytes.fromhex(rs[130:130 + 2 * ln]).decode(errors='replace')
        except Exception: s = t
        syms[t] = [s, int(dc, 16) if dc else None]
    mk[mid] = {"loan": loan, "coll": coll, "oracle": orc, "lltv": lltv / 1e18, "feeds": feeds, "syms": syms,
               "n": sum(1 for x in ev if x['id'] == mid)}
    print('market', mid[:10], mk[mid]['n'], syms, feeds, flush=True)
json.dump({"events": ev, "markets": mk}, open('chainsel-2685-rh-events.json', 'w'), indent=1)
for mid, m in sorted(mk.items(), key=lambda kv: -kv[1]['n']):
    print(m['n'], m['syms'][m['coll']][0], '/', m['syms'][m['loan']][0], 'lltv', m['lltv'], 'oracle', m['oracle'], json.dumps(m['feeds']))
