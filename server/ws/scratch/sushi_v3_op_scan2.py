import json, subprocess
from collections import Counter

def rpc(method, params):
    out = subprocess.run(['python3','/srv/farm/ws/tools/rpc.py','optimism',method,json.dumps(params)],
                         capture_output=True, text=True)
    try:
        d = json.loads(out.stdout)
    except Exception:
        raise SystemExit('bad json: '+out.stdout[:200]+out.stderr[:200])
    if 'error' in d:
        raise SystemExit('RPC error: '+str(d['error'])[:300])
    return d['result']

pools = json.load(open('/srv/farm/ws/scratch/sushi-v3-op-pools.json'))
SWAP = '0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67'
COLLECT = '0x0c396cd989a39f4459b5fa1aed6a9a8dcdbc45908acfd67e028cd568da98982c'  # from no-topic scan
FROM, TO = '0x982e0f7', 'latest'
b0 = rpc('eth_getBlockByNumber',[FROM,False]); b1 = rpc('eth_getBlockByNumber',['latest',False])
print('window', int(b0['number'],16), int(b0['timestamp'],16), '->', int(b1['number'],16), int(b1['timestamp'],16),
      'days %.2f' % ((int(b1['timestamp'],16)-int(b0['timestamp'],16))/86400), flush=True)

swap_logs, collect_logs = [], []
for i in range(0, len(pools), 32):
    batch = pools[i:i+32]
    for topic, store in ((SWAP, swap_logs), (COLLECT, collect_logs)):
        lg = rpc('eth_getLogs',[{'address':batch,'topics':[topic],'fromBlock':FROM,'toBlock':TO}])
        store.extend(lg)
    print('batch', i//32, 'cum swap', len(swap_logs), 'cum collect', len(collect_logs), flush=True)

print('TOTAL 7d Swap logs:', len(swap_logs), ' Collect logs:', len(collect_logs))
print('pools with >=1 swap:', len(set(l['address'] for l in swap_logs)), 'of', len(pools))
swappers = Counter(('0x'+l['topics'][1][26:].lower()) for l in swap_logs if len(l['topics'])>1)
print('distinct swap senders:', len(swappers))
for a,c in swappers.most_common(12): print(' ', a, c)
json.dump({'swap':swap_logs,'collect':collect_logs}, open('/srv/farm/ws/scratch/sushi-v3-op-7d-logs.json','w'))
