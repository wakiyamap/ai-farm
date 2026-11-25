import json, subprocess, sys

def rpc(method, params):
    out = subprocess.run(['python3','/srv/farm/ws/tools/rpc.py','bsc',method,json.dumps(params)],
                         capture_output=True, text=True)
    if out.returncode != 0:
        return {'_err': (out.stdout+out.stderr)[:400]}
    return json.loads(out.stdout)['result']

L = int(rpc('eth_blockNumber', []) , 16)
b0 = rpc('eth_getBlockByNumber', [hex(L), False])
b1 = rpc('eth_getBlockByNumber', [hex(L-2000), False])
t0, t1 = int(b0['timestamp'],16), int(b1['timestamp'],16)
bt = (t0-t1)/2000.0
print('latest', L, 'ts', t0, 'block_time_s', round(bt,4))
n7 = int(7*86400/bt) if bt>0 else 5000*40
print('approx blocks in 7d', n7)

V1='0x0c89c0407775dd89b12918b9c0aa42bf96518820'
V2='0x7536592bb74b5d62eb82e8b93b17eed4eed9a85c'

# probe: last 5000 blocks, both contracts, address-only filter
for a in (V1,V2):
    r = rpc('eth_getLogs', [{'fromBlock':hex(L-5000),'toBlock':hex(L),'address':a}])
    if isinstance(r, dict):
        print(a, 'ERR', r['_err'][:200])
    else:
        print(a, 'logs last 5000 blocks:', len(r))
        for e in r[:6]:
            print('   ', int(e['blockNumber'],16), e['transactionHash'][:20], e['topics'][0][:20])
