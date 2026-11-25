import re, sys, json
s = open(sys.argv[1], encoding='utf-8', errors='replace').read()
s = s.replace('\\"', '"')
nets = re.findall(r'\{"id":"([A-Z0-9_]+)","label":"([^"]+)","kebab":"([^"]+)","chain":(\d+),"mainnet":(true|false)\}', s)
# dedupe preserving first occurrence order
seen = set(); N = []
for n in nets:
    if n[0] in seen: continue
    seen.add(n[0]); N.append(n)
methods = {}
for m in re.finditer(r'\{"name":"([^"]+)","product":"([^"]+)","networks":\[([0-9,]*)\]\}', s):
    name = m.group(1)
    idx = [int(x) for x in m.group(3).split(',') if x]
    methods.setdefault(name, set()).update(idx)
print('networks', len(N), 'methods', len(methods), file=sys.stderr)
want = ['eth_blockNumber', 'eth_subscribe', 'debug_traceTransaction', 'debug_traceCall', 'trace_block', 'trace_transaction', 'eth_getLogs']
print('net | ' + ' | '.join(want))
for i, (nid, label, kebab, chain, mainnet) in enumerate(N):
    if mainnet != 'true': continue
    row = ['Y' if i in methods.get(w, ()) else '-' for w in want]
    print(f'{label} ({kebab}) | ' + ' | '.join(row))
