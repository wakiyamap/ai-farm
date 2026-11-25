import json, sys, time, urllib.request, urllib.parse

HDR = {'User-Agent': 'Mozilla/5.0 (research; farm-scout)'}

def get(u):
    r = urllib.request.Request(u, headers=HDR)
    return json.load(urllib.request.urlopen(r, timeout=30))

def addr_txs(addr, pages=4):
    out = []
    nxt = None
    for _ in range(pages):
        u = f"https://base.blockscout.com/api/v2/addresses/{addr}/transactions"
        if nxt:
            u += "?" + urllib.parse.urlencode(nxt)
        d = get(u)
        out += d.get('items', [])
        nxt = d.get('next_page_params')
        if not nxt:
            break
    return out

def meth_of(t):
    m = t.get('method')
    return m.get('method_id') if isinstance(m, dict) else m

if __name__ == '__main__':
    cutoff = "2026-11-12T05:50:00Z"
    for addr in sys.argv[1:]:
        txs = addr_txs(addr)
        counts = {}
        for t in txs:
            counts[meth_of(t)] = counts.get(meth_of(t), 0) + 1
        sk = [t for t in txs if meth_of(t) == 'skim']
        sk7 = [t for t in sk if t.get('timestamp', '') >= cutoff]
        print(addr, "txs:", len(txs), "newest:", txs[0].get('timestamp') if txs else None)
        print("   methods:", counts)
        print("   skim total pulled:", len(sk), " skim since 2026-11-12:", len(sk7))
        for t in sk[:8]:
            to = t.get('to') or {}
            print("    ", t.get('timestamp'), t.get('hash'), (to.get('hash_or_name') if isinstance(to, dict) else to),
                  "gas_used", t.get('gas_used'), "val", t.get('value'), "err", t.get('has_error'))
