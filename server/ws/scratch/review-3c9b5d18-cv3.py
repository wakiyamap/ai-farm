import json
import re
import subprocess
import time
import urllib.request
from pathlib import Path

ROOT = Path('/srv/farm/ws')
URL = 'http://127.0.0.1:9003'
OWNER = '0xc0ffee0000000000000000000000000000000001'
USDC = '0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48'
WETH = '0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2'
USDT = '0xdac17f958d2ee523a2206206994597c13d831ec7'
COMET = '0xa17581a9e3356d9a858b789d68b4d866e593ae94'
SALE = '0x4e68ccd3e89f51c3074ca5072bbac773960dfa36'
WRAP = '0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640'
HOLDER = '0x1f2f10d1c40777ae1da742455c65828ff36df387'

def rpc(method, params):
    req = urllib.request.Request(URL, json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params}).encode(), {'content-type': 'application/json'})
    result = json.loads(urllib.request.urlopen(req, timeout=120).read())
    if 'error' in result:
        raise RuntimeError((method, result['error']))
    return result['result']

def cli(*args):
    p = subprocess.run(['fork', *args], capture_output=True, text=True, check=True)
    return p.stdout.strip()

def word(v):
    return (v[2:] if isinstance(v, str) else format(v, 'x')).rjust(64, '0')

def balance(token, addr):
    return int(rpc('eth_call', [{'to': token, 'data': '0x70a08231' + word(addr)}, 'latest']), 16)

def balances(addr):
    return {name: balance(token, addr) for name, token in [('USDC', USDC), ('WETH', WETH), ('USDT', USDT)]}

def setup():
    print(cli('reset', 'ethereum', '26342224'))
    cli('fund', 'ethereum', OWNER, '3')
    out = cli('deploy', 'ethereum', str(ROOT / 'scratch/cv3-eth/creation-current.hex'), OWNER)
    addr = re.search(r'0x[0-9a-fA-F]{40}', out).group().lower()
    actual = rpc('eth_getCode', [addr, 'latest']).lower()
    expected = (ROOT / 'bots/paper/cv3-buy-watcher-ethereum/executor-runtime.hex').read_text().strip().lower()
    assert actual == expected, 'submitted runtime mismatch'
    cli('fund-token', 'ethereum', USDC, HOLDER, addr, '360000000')
    assert balances(addr) == {'USDC': 360000000, 'WETH': 0, 'USDT': 0}
    return addr

artifact = json.loads((ROOT / 'scratch/cv3-eth/contracts/out/Cv3Sniper.sol/Cv3Sniper.json').read_text())
creation = (ROOT / 'scratch/cv3-eth/creation-current.hex').read_text().strip().lower()
assert creation == artifact['bytecode']['object'].lower() + word(USDC), 'creation not current artifact plus constructor'

addr = setup()
spot = int(rpc('eth_call', [{'to': WRAP, 'data': '0x3850c7bd'}, 'latest'])[2:66], 16)
low, high = spot * 95 // 100, spot * 105 // 100
pay = 108478599869178527
floor = 3012546300548328
def calldata(min_profit):
    return '0xc1d7afaa' + ''.join(map(word, [COMET, USDT, SALE, pay, 0, min_profit, WRAP, low, high]))

def send(addr, min_profit):
    tx = {'from': OWNER, 'to': addr, 'data': calldata(min_profit), 'gas': hex(640000), 'maxFeePerGas': hex(1200000000), 'maxPriorityFeePerGas': hex(1000000000)}
    raw = cli('send', 'ethereum', json.dumps(tx))
    rec = json.loads(raw)
    hash_ = rec['transactionHash']
    return hash_, int(rec['status'], 16), int(rec['gasUsed'], 16), rec

rpc('anvil_setNextBlockBaseFeePerGas', [hex(76403909)])
before = balances(addr)
h, status, gas, rec = send(addr, floor)
after = balances(addr)
assert status == 1 and after['USDC'] > before['USDC'] and after['WETH'] == before['WETH'] and after['USDT'] == before['USDT']
profit = None
for log in rec['logs']:
    if log['address'].lower() == addr:
        profit = int(log['data'][66:130], 16)
assert profit is not None
print(json.dumps({'success': h, 'status': status, 'gas': gas, 'before': before, 'after': after, 'base_profit': profit}))

addr = setup()
rpc('anvil_setNextBlockBaseFeePerGas', [hex(76403909)])
before = balances(addr)
h, status, gas, rec = send(addr, profit + 1)
after = balances(addr)
trace = rpc('debug_traceTransaction', [h, {}])
print(json.dumps({'guard': h, 'status': status, 'gas': gas, 'reason': trace.get('revertReason'), 'before': before, 'after': after}), flush=True)
assert status == 0 and trace.get('revertReason') == 'NO_PROFIT' and after == before
print(json.dumps({'guard': h, 'status': status, 'gas': gas, 'reason': trace.get('revertReason'), 'before': before, 'after': after}))
