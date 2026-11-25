"""Proxy window for captures on non-ChainlinkOracleV2 markets: last AnswerUpdated of a proxy aggregator (same underlying) before the capture."""
import json, urllib.request, sys
url = "https://rpc.mainnet.chain.robinhood.com"
AU = '0x0559884fd3a460db3073b7fc896cc77986f16e378210ded43186175bf646fc5f'
def call(m, p):
    req = urllib.request.Request(url, data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": m, "params": p}).encode(),
                                 headers={"Content-Type": "application/json", "User-Agent": "farm-research/1"})
    j = json.load(urllib.request.urlopen(req, timeout=30))
    if 'error' in j: raise RuntimeError(j['error'])
    return j['result']
agg, blocks = sys.argv[1], [int(b) for b in sys.argv[2:]]
for B in blocks:
    lg = call('eth_getLogs', [{"address": agg, "topics": [AU], "fromBlock": hex(B - 99999), "toBlock": hex(B)}])
    ups = sorted(int(l['blockNumber'], 16) for l in lg)
    prior = [u for u in ups if u < B]
    same = [u for u in ups if u == B]
    if not prior:
        print(B, 'no update in 100k blocks', len(ups)); continue
    last = prior[-1]
    t = lambda b: int(call('eth_getBlockByNumber', [hex(b), False])['timestamp'], 16)
    print(B, 'last update', last, 'gap blocks', B - last, 'gap s', t(B) - t(last), 'update in capture block', bool(same), 'updates in 100k', len(ups))
