#!/usr/bin/env python3
"""Final details: EIP3009 usage in 7d, event details, receiver code check."""
import json, subprocess, collections

def raw(method, params):
    out = subprocess.run(['python3', '/srv/farm/ws/tools/rpc.py', 'ethereum', method, json.dumps(params)],
                         capture_output=True, text=True).stdout
    d = json.loads(out)
    if 'error' in d:
        raise SystemExit('RPC error: ' + json.dumps(d['error'])[:200])
    return d['result']

FR, TO = 26413784, 26464036
WRAP = '0xa2E3356610840701BDf5611a53974510Ae27E2e1'
UNWRAP = '0x79973d557CD9dd87eb61E250cc2572c990e20196'

def logs(addr, t0s, fr=FR, to=TO):
    return raw('eth_getLogs', [{'fromBlock': hex(fr), 'toBlock': hex(to), 'address': addr, 'topics': [t0s]}])

eip = logs(WRAP, ['0x98de503528ee59b575ef0c0a2576a82497bfc029a5685b209e9ec333479b10a5',
                  '0x1cdd46ff242716cdaa72d159d339a485b3438398348d68f09d7c8c0a59353d81'])
print('EIP3009 AuthorizationUsed/Canceled in 7d on WRAP:', len(eip))

dep = logs(WRAP, ['0xe32c4b34261b430739ef30d727d062f9fdd6410be2080e6fd875a6015f40de83'])
print('DepositEth (4 expected): users / ETH in / WBETH out')
for l in dep:
    u = '0x' + l['topics'][1][-40:]
    d = int(l['data'][2:66], 16) / 1e18
    w = int(l['data'][66:130], 16) / 1e18
    print(f"   block {int(l['blockNumber'],16)} user {u} eth {d:.4f} wbeth {w:.4f} tx {l['transactionHash']}")

rw = logs(WRAP, ['0xe1ea856a2dd2650e9ab8bb416f893add49ac95f8364e47b4395a3ada9b0ccc2c'])
print('RequestWithdrawEth on WRAP:')
for l in rw:
    print('   ', '0x' + l['topics'][1][-40:], int(l['data'][2:66], 16)/1e18, 'wbeth ->', int(l['data'][66:130], 16)/1e18, 'eth')

cw = logs(UNWRAP, ['0x11636acb273b17b8e23cc6bcaf0758c5159a25ff5df82ca4134eb012ab949e46'])
print('ClaimWithdraw on UNWRAP:')
for l in cw:
    print('   ', '0x' + l['topics'][1][-40:], int(l['data'][2:66], 16)/1e18, 'eth')

er = logs(WRAP, ['0x0b4e9390054347e2a16d95fd8376311b0d2deedecba526e9742bcaa40b059f0b'])
print('ExchangeRateUpdated rates:', [round(int(l['data'][2:66], 16)/1e18, 6) for l in er])
print('  tx hashes:', sorted({l['transactionHash'] for l in er}))

for name, a in [('ethReceiver', '0x26ad6395dabf271fd9bfdc82d7377261930e6b86'),
                ('oracle', '0x81720695e43a39c52557ce6386feb3faac215f06'),
                ('operator', '0x2b59215778e99035cf38663454ef1240a7ae70f5')]:
    c = raw('eth_getCode', [a, 'latest'])
    print(f'{name} {a} code len {(len(c)-2)//2}')
