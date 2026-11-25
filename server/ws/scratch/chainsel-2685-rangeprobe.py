"""Probe public RPCs of a chainId (chainid.network list) for eth_getLogs range limits and archive eth_call depth."""
import json, sys, urllib.request
cid, addr, topic = int(sys.argv[1]), sys.argv[2], sys.argv[3]
cl = json.load(urllib.request.urlopen(urllib.request.Request("https://chainid.network/chains.json", headers={"User-Agent": "farm-research/1"}), timeout=30))
c = [x for x in cl if x['chainId'] == cid][0]
urls = sys.argv[4:] or [u for u in c.get('rpc', []) if u.startswith('https://') and '${' not in u]
print(c['name'], urls)
def call(url, m, p):
    req = urllib.request.Request(url, data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": m, "params": p}).encode(),
                                 headers={"Content-Type": "application/json", "User-Agent": "farm-research/1"})
    return json.load(urllib.request.urlopen(req, timeout=15))
for u in urls[:8]:
    try:
        h = int(call(u, 'eth_blockNumber', [])['result'], 16)
    except Exception as e:
        print(u, 'down', str(e)[:60]); continue
    out = [u, h]
    for r in [500000, 100000, 10000, 1000, 100]:
        try:
            j = call(u, 'eth_getLogs', [{"address": addr, "topics": [topic], "fromBlock": hex(h - r), "toBlock": hex(h)}])
            out.append((r, len(j['result']) if 'result' in j else j['error'].get('message', '')[:50]))
            if 'result' in j: break
        except Exception as e:
            out.append((r, str(e)[:40]))
    for d in [1000, 100000, 3000000]:
        try:
            j = call(u, 'eth_getBalance', [addr, hex(h - d)])
            out.append(('state-' + str(d), 'ok' if 'result' in j else j['error'].get('message', '')[:40]))
        except Exception as e:
            out.append(('state-' + str(d), str(e)[:40]))
    print(out, flush=True)
