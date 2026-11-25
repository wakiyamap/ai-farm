import urllib.request, json, sys

addr = sys.argv[1]
out = sys.argv[2]
url = f'https://bsc.blockscout.com/api/v2/smart-contracts/{addr}'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (research)'})
r = urllib.request.urlopen(req, timeout=30)
d = json.load(r)
print('name:', d.get('name'))
print('verified:', d.get('is_verified'), '| compiler:', d.get('compiler_version'))
abi = d.get('abi') or []
print('abi entries:', len(abi))
open(out, 'w').write(json.dumps(abi))
for f in abi:
    if f.get('type') == 'function':
        ins = ','.join(i['type'] for i in f.get('inputs', []))
        outs = ','.join(o['type'] for o in f.get('outputs', []))
        print(f"{f['stateMutability']:9s} {f['name']}({ins}) -> {outs}")
    elif f.get('type') == 'event':
        ins = ','.join(i['type'] + (' indexed' if i.get('indexed') else '') for i in f.get('inputs', []))
        print(f"event {f['name']}({ins})")
