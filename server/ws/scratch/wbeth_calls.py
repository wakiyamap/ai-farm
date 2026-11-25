#!/usr/bin/env python3
"""eth_call the WBETH wrap/unwrap functions from a fresh address; show revert reasons."""
import json, subprocess

FRESH = '0x' + '0' * 34 + 'c0ffee'
ADDRARG = '0' * 24 + FRESH[2:]
WRAP = '0xa2E3356610840701BDf5611a53974510Ae27E2e1'
UNWRAP = '0x79973d557CD9dd87eb61E250cc2572c990e20196'

def raw(method, params):
    out = subprocess.run(['python3', '/srv/farm/ws/tools/rpc.py', 'ethereum', method, json.dumps(params)],
                         capture_output=True, text=True).stdout
    return json.loads(out)

def reason(d):
    if 'error' in d:
        msg = d['error'].get('message', '')
        return 'REVERT: ' + (msg.split('execution reverted')[-1].strip() or msg)
    return 'OK, returns ' + str(d['result'])[:70]

def call(to, data, label):
    print(f'{label:<34} {reason(raw("eth_call", [{"from": FRESH, "to": to, "data": data}, "latest"]))}')

call(WRAP, '0xb9e205ae' + '%064x' % 1100000000000000000, 'updateExchangeRate(1.1e18)')
call(WRAP, '0x1c439430', 'supplyEth()')
call(WRAP, '0x824da34f' + '%064x' % 1, 'moveToStakingAddress(1)')
call(WRAP, '0x0ab9aaf6' + '%064x' % 1, 'moveToUnwrapAddress(1)')
call(WRAP, '0xa0712d68' + '%064x' % 1, 'mint(1)')
call(WRAP, '0xa0907283' + '%064x' % 1, 'requestWithdrawEth(1)')
call(WRAP, '0xf340fa01' + ADDRARG, 'deposit(fresh)')
call(UNWRAP, '0x90ca796b' + '%064x' % 1, 'allocate(1)')
call(UNWRAP, '0xb13acedd' + '%064x' % 0, 'claimWithdraw(0)')
call(UNWRAP, '0x3a2bf94e' + ADDRARG + '%064x%064x' % (1, 1), 'requestWithdraw(fresh,1,1)')
call(UNWRAP, '0x5102e377', 'getNeedRechargeEthAmount()')
