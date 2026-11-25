import json, subprocess, sys

def rpc(method, params):
    r = subprocess.run(['python3','/srv/farm/ws/tools/rpc.py','ethereum',method,json.dumps(params)],
                       capture_output=True, text=True)
    try:
        d = json.loads(r.stdout)
    except Exception:
        print('RPC ERR', method, r.stdout[:200], r.stderr[:200]); return None
    if 'error' in d:
        print('RPC error', method, d['error'].get('message'), str(d['error'])[:200]); return None
    return d['result']

def blockts(n):
    b = rpc('eth_getBlockByNumber',[hex(n), False])
    if b is None: return None
    return int(b['timestamp'],16)

LATEST = 26464575
LAT_TS = 1795277339
TARGET = LAT_TS - 7*86400

# binary search
lo, hi = LATEST-60000, LATEST
while lo < hi:
    mid = (lo+hi)//2
    ts = blockts(mid)
    if ts is None:
        print('search failed at', mid); sys.exit(1)
    if ts < TARGET: lo = mid+1
    else: hi = mid
B7 = lo
print('7d-ago block', B7, blockts(B7), 'target', TARGET)

VAULTS = json.load(open('scratch/flokifi_vaults.json'))
FACTORY = '0xc64c475523404759de6991ba8a71c7574e04245a'
KEY = '0xd7df4d751a16a6e2a68c1a383e6aee94baff7a9f'

TRANSFER_TOPIC = '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
def pad(a): return '0x'+'0'*24+a.lower()[2:]

# 1) factory events in last 7d (any topic)
logs = rpc('eth_getLogs',[{'fromBlock':hex(B7),'toBlock':hex(LATEST),'address':FACTORY}])
print('factory logs 7d:', None if logs is None else len(logs))
if logs:
    from collections import Counter
    c = Counter(l['topics'][0] for l in logs)
    print('factory topic0:', dict(c))
    for l in logs[:5]:
        print(' ', l['transactionHash'], int(l['blockNumber'],16), l['topics'][0])

# 2) VaultKey transfers 7d (any direction)
logs = rpc('eth_getLogs',[{'fromBlock':hex(B7),'toBlock':hex(LATEST),'address':KEY,'topics':[TRANSFER_TOPIC]}])
print('vaultkey Transfer 7d:', None if logs is None else len(logs))
if logs:
    for l in logs[:10]:
        frm = l['topics'][1][26:]; to = l['topics'][2][26:]
        val = int(l['data'],16)
        print(' tx', l['transactionHash'], 'blk', int(l['blockNumber'],16), 'from', frm, 'to', to, 'id', val)

# 3) vault activity: chunk vaults by 32, scan Transfer logs where vault is sender OR receiver
#    getLogs can't AND from-topic with address list beyond 32; use from-topic = vault (transfer FROM vault = withdrawal)
from_hex = pad
withdrawals = []
for i in range(0, len(VAULTS), 32):
    chunk = VAULTS[i:i+32]
    # transfers FROM vaults: topics [TRANSFER, vault-padded]
    logs = rpc('eth_getLogs',[{'fromBlock':hex(B7),'toBlock':hex(LATEST),'address':None,'topics':[TRANSFER_TOPIC, [pad(v) for v in chunk]]}])
    if logs is None:
        print('chunk', i, 'FAILED'); continue
    print('withdrawal chunk', i//32, len(chunk), 'vaults ->', len(logs), 'logs')
    withdrawals += logs
print('total withdrawals-from-vault 7d:', len(withdrawals))
for l in withdrawals[:15]:
    frm = l['topics'][1][26:]; to = l['topics'][2][26:]
    print(' tx', l['transactionHash'], 'from', frm, 'to', to, 'raw', int(l['data'],16), 'token', l['address'])

# control: same query shape on USDC from-topic over last 1000 blocks
CTL = '0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48'
logs = rpc('eth_getLogs',[{'fromBlock':hex(LATEST-1000),'toBlock':hex(LATEST),'address':CTL,'topics':[TRANSFER_TOPIC]}])
print('control USDC Transfers last 1000 blocks:', None if logs is None else len(logs))
