import json
from vertexlib import post, head_of

topic0 = '0x494f937f5cc892f798248aa831acfb4ad7c4bf35edd8498c5fb431ce1e38b035'

if __name__ == '__main__':
    import sys
    chain = sys.argv[1]
    nwins = int(sys.argv[2]) if len(sys.argv) > 2 else 20
    span = 29999
    head = head_of(chain)
    batch = []
    for i in range(nwins):
        to = head - i * span
        frm = to - span
        batch.append({"jsonrpc": "2.0", "id": i, "method": "eth_getLogs",
                      "params": [{"topics": [topic0], "fromBlock": hex(frm), "toBlock": hex(to)}]})
    # split batches of 10 to respect relay batch caps
    logs = []
    errs = []
    for b in range(0, nwins, 10):
        out = post(chain, batch[b:b + 10])
        for o in out:
            res = o.get('result')
            if res is None:
                errs.append(o.get('error'))
            else:
                logs.extend(res)
    print('chain', chain, 'windows', nwins, 'head', hex(head), 'liquidation logs', len(logs), 'errors', len(errs), (errs[0] if errs else None))
    addrs = {}
    for l in logs:
        addrs[l['address']] = addrs.get(l['address'], 0) + 1
    print(sorted(addrs.items(), key=lambda x: -x[1])[:8])
    for l in logs[:12]:
        print(l['blockNumber'], l['address'], l['topics'][1][:18], l['topics'][2][:18], l['data'][:80])
