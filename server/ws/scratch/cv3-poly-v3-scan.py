#!/usr/bin/env python3
"""Fresh 7d scan: BuyCollateral / AbsorbCollateral on polygon Compound v3 cUSDCv3 + cUSDTv3."""
import json, subprocess, time

def rpc(chain, method, params):
    out = subprocess.run(['python3', '/srv/farm/ws/tools/rpc.py', chain, method, json.dumps(params)],
                         capture_output=True, text=True)
    try:
        j = json.loads(out.stdout)
    except Exception:
        return {'error': (out.stdout + out.stderr)[:300]}
    return j.get('result', j) if isinstance(j, dict) else j

USDCv3 = '0xF25212E676D1F7F89Cd72fFEe66158f541246445'
USDTv3 = '0xaeB318360f27748Acb200CE616E389A6C9409a07'
T_ABS = '0x9850ab1af75177e4a9201c65a2cf7976d5d28e40ef63494b44366f86b2f9412e'  # AbsorbCollateral(address,address,address,uint256,uint256)
T_BUY = '0xf891b2a411b0e66a5f0a6ff1368670fefa287a13f541eb633a386a1a9cc7046b'  # BuyCollateral(address,address,uint256,uint256)

# code check + getter
for a in (USDCv3, USDTv3):
    code = rpc('polygon', 'eth_getCode', [a, 'latest'])
    sbase = subprocess.run(['/opt/foundry/bin/cast', 'sig', 'baseToken()'], capture_output=True, text=True).stdout.strip()
    base = rpc('polygon', 'eth_call', [{'to': a, 'data': sbase}, 'latest'])  # baseToken()
    print(a, 'codelen', len(code)//2-1 if isinstance(code, str) else code, 'baseToken', base if isinstance(base, str) else 'ERR')

head = int(rpc('polygon', 'eth_blockNumber', []), 16)
hb = rpc('polygon', 'eth_getBlockByNumber', [hex(head), False]); ts = int(hb['timestamp'], 16)
ob = rpc('polygon', 'eth_getBlockByNumber', [hex(head - 300000), False]); dt = ts - int(ob['timestamp'], 16)
span = int(300000 * 7 * 86400 / dt)
start = head - span
print('head', head, 'ts', ts, '7d span', span, 'start', start)

logs, errs, b, step = [], 0, start, 10000
while b <= head:
    e = min(b + step - 1, head)
    r = rpc('polygon', 'eth_getLogs', [{'address': [USDCv3, USDTv3], 'topics': [[T_ABS, T_BUY]], 'fromBlock': hex(b), 'toBlock': hex(e)}])
    if not isinstance(r, list):
        errs += 1; print('err', b, e, str(r)[:150]); time.sleep(1)
        if errs > 6: break
        continue
    logs += r; b = e + 1
print('logs', len(logs), 'errs', errs)

out = []
for l in sorted(logs, key=lambda x: int(x['blockNumber'], 16)):
    kind = 'ABS' if l['topics'][0] == T_ABS else 'BUY'
    d = l['data'][2:]
    nums = [int(d[i:i+64], 16) for i in range(0, len(d), 64)]
    idx = ['0x' + t[26:].lower() for t in l['topics'][1:]]
    rec = {'kind': kind, 'block': int(l['blockNumber'], 16), 'tx': l['transactionHash'], 'idx': int(l['transactionIndex'], 16),
           'cm': 'usdc' if l['address'].lower() == USDCv3.lower() else 'usdt', 'idx_addrs': idx, 'data': nums}
    out.append(rec)
    print(kind, rec['block'], 'txidx', rec['idx'], rec['cm'], idx, nums)
json.dump({'head': head, 'start': start, 'ts': ts, 'logs': out}, open('/srv/farm/ws/scratch/cv3-poly-v3-scan.json', 'w'))
