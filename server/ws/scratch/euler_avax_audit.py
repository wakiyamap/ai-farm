import json
import os
import time
import urllib.request
from pathlib import Path

ROOT = Path('/srv/farm/ws/scratch/euler_avax_audit')
ROOT.mkdir(exist_ok=True)
URL = os.environ['RPC_RELAY_URL'].rstrip('/') + '/avalanche'
FACTORY = '0xaf4B4c18B17F6a2B32F6c398a3910bdCD7f26181'

def rpc(method, params):
    payload = json.dumps({'jsonrpc':'2.0','id':1,'method':method,'params':params}).encode()
    req = urllib.request.Request(URL, payload, {'Content-Type':'application/json'})
    with urllib.request.urlopen(req, timeout=45) as res:
        data = json.load(res)
    if 'error' in data:
        raise RuntimeError(data['error'])
    return data['result']

def call(to, data):
    return rpc('eth_call', [{'to':to,'data':data},'latest'])

head = int(rpc('eth_blockNumber', []), 16)
length = int(call(FACTORY, '0x0a68b7ba'), 16)
vaults = []
for i in range(length):
    raw = call(FACTORY, '0x378cdb62' + f'{i:064x}')
    address = '0x' + raw[-40:]
    borrow = int(call(address, '0x47bd3718'), 16)
    if borrow:
        vaults.append({'index':i,'address':address,'totalBorrowsRaw':str(borrow)})
    if i and i % 50 == 0:
        print('vaults', i, 'borrowed', len(vaults), flush=True)

(ROOT/'vaults.json').write_text(json.dumps({'head':head,'factory':FACTORY,'length':length,'borrowed':vaults},indent=2))
print('borrowed', len(vaults), 'head', head, flush=True)

# Avalanche block spacing is variable. This range deliberately overcovers seven days.
# Each page is <= 10,000 blocks per relay limits; logs are address-filtered with no topic.
start = max(0, head - 360000)
addresses = [v['address'] for v in vaults]
seen = {}
failures = []
for lo in range(start, head+1, 10000):
    hi = min(head, lo+9999)
    try:
        logs = rpc('eth_getLogs', [{'fromBlock':hex(lo),'toBlock':hex(hi),'address':addresses}])
        for log in logs:
            t = log['topics'][0] if log['topics'] else '(none)'
            entry = seen.setdefault(t, {'count':0,'first_block':None,'last_block':None,'example':None})
            block = int(log['blockNumber'],16)
            entry['count'] += 1
            entry['first_block'] = min(entry['first_block'] or block, block)
            entry['last_block'] = max(entry['last_block'] or block, block)
            if entry['example'] is None:
                entry['example'] = log
    except Exception as exc:
        failures.append({'lo':lo,'hi':hi,'error':str(exc)})
    print('page',lo,hi,'topics',len(seen),'failures',len(failures),flush=True)
    time.sleep(0.03)
(ROOT/'scan.json').write_text(json.dumps({'head':head,'start':start,'end':head,'addresses':addresses,'topics':seen,'failures':failures},indent=2))
