import json
from vertexlib import post, head_of

topic0 = '0x494f937f5cc892f798248aa831acfb4ad7c4bf35edd8498c5fb431ce1e38b035'

def scan(chain, span, back):
    head = head_of(chain)
    frm = head - span - back
    o = post(chain, [{"jsonrpc": "2.0", "id": 2, "method": "eth_getLogs",
                      "params": [{"topics": [topic0], "fromBlock": hex(frm), "toBlock": hex(head - back)}]}])[0]
    res = o.get('result')
    print(chain, 'window', hex(frm), hex(head - back), 'logs', None if res is None else len(res), o.get('error'))
    if res:
        addrs = {}
        for l in res:
            addrs[l['address']] = addrs.get(l['address'], 0) + 1
        print(sorted(addrs.items(), key=lambda x: -x[1])[:6])

if __name__ == '__main__':
    import sys
    chain, span, back = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
    scan(chain, span, back)
