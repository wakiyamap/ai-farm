import json, subprocess

RPC = ['python3', '/srv/farm/ws/tools/rpc.py', 'avalanche']
def call(method, params):
    out = subprocess.run(RPC + [method, json.dumps(params)], capture_output=True, text=True)
    if out.returncode != 0:
        raise RuntimeError(f'{method} failed: {out.stderr[:300]}')
    return json.loads(out.stdout)['result']

logs = json.load(open('scratch/beefy-avax-scout-logs.json'))
ev = []
for l in logs:
    d = l['data'][2:]
    caller_fee = int(d[0:64], 16)
    ev.append((caller_fee, l['transactionHash'], l['address']))
ev.sort(reverse=True)
print('first-word (caller) fee: max', ev[0][0]/1e18, 'sum', sum(e[0] for e in ev)/1e18, 'WAVAX')

for fee, txh, addr in ev[:5]:
    r = call('eth_getTransactionReceipt', [txh])
    gwei = int(r['effectiveGasPrice'], 16) * int(r['gasUsed'], 16) / 1e18
    print(f'tx {txh[:20]}.. from {r["from"]} fee {fee/1e18:.9f} WAVAX gasUsed {int(r["gasUsed"],16)} gasAVAX {gwei:.6f}')
