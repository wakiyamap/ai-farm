import json
import subprocess

MORPHO = '0xbbbbbbbbbb9cc5e90e3b3af64bdaf62c37eeffcb'
MARKET = '0x0ca10126f6c94cbd9cf0a48cc9516ae5e3dec5aa68303e6d988ee37c5149bf0d'
PARAMS = '(0x833589fcd6edb6e08f4c7c32d4f71b54bda02913,0x2ae3f1ec7f1f5012cfeab0185bfc7aa3cf0dec22,0x97ff9cbd7e77348b2b8ffbb883bf29452ad18295,0x46415998764c29ab2a25cbea6254146d50d22687,770000000000000000)'
BORROWER = '0xa2bd6bd30a0eae32faed711fcd9c15d1fcb4da3e'
CAST = '/opt/foundry/bin/cast'


def calldata(sig, *args):
    return subprocess.check_output([CAST, 'calldata', sig, *args], text=True).strip()


def rpc(method, params):
    p = subprocess.run(['python3', '/srv/farm/ws/tools/rpc.py', 'base', method,
                        json.dumps(params), '--lane', 'research'], text=True,
                       capture_output=True)
    return {'request': {'method': method, 'params': params},
            'exit': p.returncode, 'response': json.loads(p.stdout)}


getter = calldata('idToMarketParams(bytes32)', MARKET)
liquidate = calldata('liquidate((address,address,address,address,uint256),address,uint256,uint256,bytes)',
                     PARAMS, BORROWER, '0', '7817652371541', '0x')
evidence = {'getter': rpc('eth_call', [{'to': MORPHO, 'data': getter}, '0x350f066'])}
for block in (55636060, 55636068, 55636069, 55636070, 55636071):
    evidence[str(block)] = rpc('eth_call', [{'from': '0x1111111111111111111111111111111111111111',
                                            'to': MORPHO, 'data': liquidate}, hex(block)])
with open('/srv/farm/ws/scratch/lead220-entry-probe.json', 'w') as f:
    json.dump(evidence, f, indent=2)
for key in ('getter', '55636060', '55636068', '55636069', '55636070', '55636071'):
    print(key, evidence[key]['response'].get('result', evidence[key]['response'].get('error', {}).get('message')))
