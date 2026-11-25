import json, subprocess, sys

def rpc(method, params):
    out = subprocess.run(['python3','/srv/farm/ws/tools/rpc.py','optimism',method,json.dumps(params)],
                         capture_output=True, text=True)
    d = json.loads(out.stdout)
    if 'error' in d:
        raise SystemExit('RPC error: '+str(d['error'])[:300])
    return d['result']

pools = json.load(open('/srv/farm/ws/scratch/sushi-v3-op-pools.json'))
FROM, TO = 159601207, 159903607   # 7d window (see timestamps printed below)
b = rpc('eth_getBlockByNumber',[hex(FROM),False]); c = rpc('eth_getBlockByNumber',[hex(TO),False])
print('window blocks', FROM, int(b['timestamp'],16), '->', TO, int(c['timestamp'],16),
      'days', (int(c['timestamp'],16)-int(b['timestamp'],16))/86400)

SWAP = '0xb199a4f0d4f6d1e0ddd5b3e1b3e0b3a'  # placeholder replaced below
from_swaps = {}
total = 0
CHUNK = 32
logs_all = []
for i in range(0, len(pools), CHUNK):
    batch = pools[i:i+CHUNK]
    try:
        lg = rpc('eth_getLogs',[{'address':batch,'topics':[SWAP],'fromBlock':hex(FROM),'toBlock':hex(TO)}])
    except SystemExit as e:
        print('batch fail', i, e); continue
    total += len(lg)
    logs_all.extend(lg)
    print('batch', i//CHUNK, 'logs', len(lg), flush=True)
print('TOTAL swap logs in 7d:', total)
json.dump(logs_all, open('/srv/farm/ws/scratch/sushi-v3-op-swaps.json','w'))
