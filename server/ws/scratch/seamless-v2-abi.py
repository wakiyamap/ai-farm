import json, sys
abi = json.load(open('/srv/farm/ws/scratch/lm-impl-abi.json'))
if isinstance(abi, dict):
    abi = abi.get('ABI') or abi.get('abi') or []
fns = [i for i in abi if i.get('type') == 'function']
def sig(f):
    return f['name'] + '(' + ','.join(i['type'] for i in f['inputs']) + ')'
nonview = sorted({sig(f) for f in fns if f['stateMutability'] not in ('view', 'pure')})
views = sorted({f['name'] for f in fns if f['stateMutability'] in ('view', 'pure')})
evs = [i for i in abi if i.get('type') == 'event']
print('NON-VIEW:')
for x in nonview:
    print('  ', x)
print('VIEWS:', ', '.join(views))
print('EVENTS:')
for e in evs:
    print('  ', e['name'] + '(' + ','.join(('indexed ' if i.get('indexed') else '') + i['type'] for i in e['inputs']) + ')')
