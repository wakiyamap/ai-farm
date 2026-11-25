import json, subprocess
from collections import Counter

def rpc(method, params, tries=3):
    for t in range(tries):
        out = subprocess.run(['python3','/srv/farm/ws/tools/rpc.py','optimism',method,json.dumps(params)],
                             capture_output=True, text=True)
        try:
            d = json.loads(out.stdout)
        except Exception:
            continue
        if 'error' in d:
            last = str(d['error'])
            continue
        return d['result']
    raise RuntimeError('fail: '+last[:160])

pools = json.load(open('/srv/farm/ws/scratch/sushi-v3-op-pools.json'))
SWAP = '0xc42079f94a6350d7e6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67'.replace('6350d7e6350d7e','6350d7')
SWAP = '0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67'
COLLECT = '0x0c396cd989a39f4459b5fa1aed6a9a8dcdbc45908acfd67e028cd568da98982c'
TO = int(rpc('eth_blockNumber',[])['result'] if isinstance(rpc('eth_blockNumber',[]),dict) else '0',16)
TO = int(rpc('eth_blockNumber',[]),16)
FROM = TO - 302400
b0 = rpc('eth_getBlockByNumber',[hex(FROM),False]); b1 = rpc('eth_getBlockByNumber',[hex(TO),False])
print('window', FROM, int(b0['timestamp'],16), '->', TO, int(b1['timestamp'],16),
      'days %.2f' % ((int(b1['timestamp'],16)-int(b0['timestamp'],16))/86400), flush=True)

def getlogs(addrs, f, t, topic, depth=0):
    try:
        return rpc('eth_getLogs',[{'address':addrs,'topics':[topic],'fromBlock':hex(f),'toBlock':hex(t)}])
    except RuntimeError as e:
        if t - f <= 10000 or depth > 6: raise
        mid = (f+t)//2
        return getlogs(addrs,f,mid,topic,depth+1) + getlogs(addrs,mid+1,t,topic,depth+1)

swap_logs, collect_logs = [], []
for i in range(0, len(pools), 32):
    batch = pools[i:i+32]
    swap_logs += getlogs(batch, FROM, TO, SWAP)
    collect_logs += getlogs(batch, FROM, TO, COLLECT)
    print('batch %d/%d cum swap %d collect %d' % (i//32+1, (len(pools)+31)//32, len(swap_logs), len(collect_logs)), flush=True)

print('TOTAL 7d Swap logs:', len(swap_logs), ' Collect logs:', len(collect_logs))
print('pools with >=1 swap:', len(set(l['address'].lower() for l in swap_logs)), 'of', len(pools))
swappers = Counter(('0x'+l['topics'][1][26:].lower()) for l in swap_logs if len(l['topics'])>1)
print('distinct swap senders:', len(swappers))
for a,c in swappers.most_common(12): print(' ', a, c)
poolsel = Counter(l['address'].lower() for l in swap_logs)
print('top pools by swaps:', poolsel.most_common(6))
print('collect recipients:', Counter(('0x'+l['topics'][2][26:].lower()) for l in collect_logs if len(l['topics'])>2).most_common(6))
json.dump({'swap':swap_logs,'collect':collect_logs,'from':FROM,'to':TO}, open('/srv/farm/ws/scratch/sushi-v3-op-7d-logs.json','w'))
