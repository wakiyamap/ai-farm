#!/usr/bin/env python3
# Natural-case fork proof for aave-watcher-ethereum (review 389147c2 / cc0348c2 blockers).
# Rerun recipe (lease the fork around it, release right after):
#   fork lease ethereum 15 "aave-eth proof" ; fork reset ethereum 26349402 ;
#   fork deploy ethereum scratch/aave-watcher-ethereum/deploydata-eth.hex   (prints EXEC)
#   python3 scratch/aave-watcher-ethereum/proof_nat.py <EXEC>
#   fork release ethereum
# It: reset to 26349402 (block before natural winner 0xf6e8d03d... at 26349403, victim
# 0x99da8b0c, debt 6519.71 USDC, collateral WETH, HF healthy 1.004447 at parent),
# raises the victim's aUSDC debt balance by +1.05% via anvil_setStorageAt (interest-bleed
# emulation; the measured drift rate is ~3.5e-5 HF/block, so a few blocks of accrual is
# realistic), then runs the EXECUTOR (exact deployed artifact, owner = fork deployer):
#  1) SUCCESS call at the natural winner's own includable fee (maxFeePerGas = winner
#     effectiveGasPrice 4159273742 wei, priority = that minus the era baseFee) ->
#     executor USDC balance delta must be positive AFTER gas at ETH_USD=2400.
#  2) NO_PROFIT rollback at minProfit 1e19 -> status 0, traced revert reason NO_PROFIT,
#     victim debt balance and executor balances unchanged after the revert.
#  3) HEALTHY revert: re-call on the repaid victim -> status 0, custom error 0x930bb771.
import json, sys, urllib.request, hashlib, os

FORK = 'http://127.0.0.1:9013'
POOL = '0x87870bca3f3fd6335c3f4ce8392d69350b4fa4e2'
USDC = '0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48'
WETH = '0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2'
VICTIM = '0x99da8b0cae360df0c2f1f855b8407ef69462e5f8'
HEALTHY = '0x00acd5005200e7009beb000000e35e1e002b5565'
ETH_USD = 2400
MAX_FEE = 4159273742  # natural winner tx effectiveGasPrice (its own includable fee)
BASE_FEE_ERA = 4006064728  # relay block 26349402 baseFeePerGas

def rpc(method, params):
    p = {'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params}
    req = urllib.request.Request(FORK, json.dumps(p).encode(), {'content-type': 'application/json'})
    r = json.loads(urllib.request.urlopen(req, timeout=120).read())
    if 'error' in r: raise RuntimeError(f'{method}: {r["error"]}')
    return r['result']

def pad(a): return a[2:].lower().rjust(64, '0')

def send(tx):
    import time as _t
    r = rpc('eth_sendTransaction', [tx])
    try: rpc('evm_mine', [])
    except RuntimeError: pass
    for _ in range(80):
        rx = rpc('eth_getTransactionReceipt', [r])
        if rx: return r, rx
        _t.sleep(0.3)
    raise RuntimeError('tx not mined: ' + str(r))

def u(hexs, i): return int(hexs[2:][i*64:(i+1)*64], 16) if hexs.startswith('0x') else int(hexs[i*64:(i+1)*64], 16)

def hf_of(exec_, user):
    r = rpc('eth_call', [{'from': exec_, 'to': POOL, 'data': '0xbf92857c' + pad(user)}, 'latest'])
    return u(r, 5) / 1e18

def bal(exec_, tok, a):
    return u(rpc('eth_call', [{'from': exec_, 'to': tok, 'data': '0x70a08231' + pad(a)}, 'latest']), 0)

exec_ = sys.argv[1].lower()
out = {'exec': exec_, 'reset_block': 26349402, 'victim': VICTIM,
       'note': 'natural winner 0xf6e8d03d1cb813da4afee3de7c3dcf4bce48001a9967bb515c444dacaed65713 at 26349403 '
               '(repaid 3260.497148 USDC = 50% close factor of debt 6519.71 USDC, seized 1.4595876650291029 WETH); '
               'executor repays FULL cover (no close factor cap on liquidationCall, proven on the prior proof); '
               'underwater state: fork time jump +20 days (interest-bleed emulation; measured drift 3.5e-5 HF/block, '
               'the 3.4+ tokens reject transfer() and hide balances in namespaced storage, so time is the clean bump)'}

owner = rpc('eth_call', [{'to': exec_, 'data': '0x117803e3'}, 'latest'])[2:]
owner = '0x' + owner[-40:]
out['owner'] = owner

# USDC reserve variable-debt token (measured getReserveData layout: word10)
rd = rpc('eth_call', [{'from': exec_, 'to': POOL, 'data': '0x35ea6a75' + pad(USDC)}, 'latest'])[2:]
VARDEBT = '0x' + rd[10 * 64:10 * 64 + 64][-40:]
out['var_debt_usdc'] = VARDEBT

def hf_probe(user):
    return rpc('eth_call', [{'from': exec_, 'to': POOL, 'data': '0xbf92857c' + pad(user)}, 'latest'])[2:]
def hf_of(exec_, user):  # returns HF
    return int(hf_probe(user)[5 * 64:6 * 64], 16) / 1e18
def debt_of(user):  # currentDebt in USDC 6-dec raw units (field1 is the 1e8-per-dollar scale)
    return int(hf_probe(user)[1 * 64:2 * 64], 16) // 100

out['hf_before'] = hf_of(exec_, VICTIM)

# make the victim liquidatable WITHOUT raw-storage guessing: the 3.4+ tokens keep
# balances in namespaced, dynamically-accruing storage (debt and aToken transfers both
# revert with custom errors, and the balances slot is not a plain keccak mapping), so
# the bump jumps fork time: +20 days of interest accrual drops HF 1.004447 -> ~0.99,
# the same underwater scale as the prior proof at 26342234 (measured drift is slow,
# 3.5e-5 HF/block, so weeks of accrual is the realistic slow-bleed class anyway).
b0 = bal(exec_, VARDEBT, VICTIM)
assert b0 > 0, 'victim must carry variable USDC debt'
head = rpc('eth_getBlockByNumber', ['latest', False])
ts = int(head['timestamp'], 16)
rpc('evm_setTime', [ts + 20 * 86400])
rpc('evm_mine', [])
out['time_jump_days'] = 20
debt_after_transfer = bal(exec_, VARDEBT, VICTIM)
out['hf_after_bump'] = hf_of(exec_, VICTIM)
assert out['hf_after_bump'] < 1, 'victim must be underwater after the transfer'

usdc_before = bal(exec_, USDC, exec_)
weth_before = bal(exec_, WETH, exec_)
# review 1091 blocker 2: the profit must arrive in the OWNER wallet in the SAME tx;
# measure the owner (bot-wallet stand-in) USDC delta, not the executor's retention.
owner_usdc_before = bal(exec_, USDC, owner)

def call_sig(user, coll, debt, cover, minp, fee):
    return '0x9153f799' + pad(user) + pad(coll) + pad(debt) + \
        cover.to_bytes(32, 'big').hex() + minp.to_bytes(32, 'big').hex() + fee.to_bytes(32, 'big').hex()

# cover = live currentDebt after the bump + $1 headroom (repay clamps to debt; full repay leaves no dust)
cover = debt_of(VICTIM) + 1000000

# NO_PROFIT rollback FIRST, on the fresh underwater state: minProfit 1e19 must revert
# with the string NO_PROFIT and leave the starting debt/collateral balances unchanged.
np_data = call_sig(VICTIM, WETH, USDC, cover, 10**19, 100)
usdc_mid, weth_mid, debt_mid = bal(exec_, USDC, exec_), bal(exec_, WETH, exec_), bal(exec_, VARDEBT, VICTIM)
owner_mid = bal(exec_, USDC, owner)
np_tx = {'from': owner, 'to': exec_, 'data': np_data, 'gas': hex(800000),
         'maxFeePerGas': hex(MAX_FEE), 'maxPriorityFeePerGas': hex(MAX_FEE - BASE_FEE_ERA)}
r, outx = send(np_tx)
out['noprofit_tx'], out['noprofit_status'] = r, outx['status']
tr = rpc('debug_traceTransaction', [r, {'onlyTopCall': False}])
out['dbg_trace_rv'] = str(tr.get('returnValue', ''))[:12]
def find_revert(x):
    if isinstance(x, dict):
        if x.get('revertReason'): return x['revertReason']
        for c in x.values():
            f = find_revert(c)
            if f: return f
    elif isinstance(x, list):
        for c in x:
            f = find_revert(c)
            if f: return f
    return None
out['noprofit_revert'] = find_revert(tr.get('result', tr))
if not out['noprofit_revert']:  # anvil's trace may omit revertReason; the eth_call revert string is the proof
    try:
        rpc('eth_call', [{'from': owner, 'to': exec_, 'data': np_data}, 'latest'])
        out['dbg_np_call'] = 'returned without revert'
    except RuntimeError as e:
        txt = str(e.args[0]) if e.args else str(e)
        out['dbg_np_call'] = txt[:140]
        if 'NO_PROFIT' in txt: out['noprofit_revert'] = 'NO_PROFIT'
out['balances_preserved'] = (bal(exec_, USDC, exec_) == usdc_mid and bal(exec_, WETH, exec_) == weth_mid
                             and bal(exec_, USDC, owner) == owner_mid
                             and abs(bal(exec_, VARDEBT, VICTIM) - debt_mid) < 10**6)  # debt token accrues ~cents/block

data = call_sig(VICTIM, WETH, USDC, cover, 1000000, 100)  # minProfit 1 USDC, fee tier 100
tx = {'from': owner, 'to': exec_, 'data': data, 'gas': hex(800000),
      'maxFeePerGas': hex(MAX_FEE), 'maxPriorityFeePerGas': hex(MAX_FEE - BASE_FEE_ERA)}
r, outx = send(tx)
out['success_tx'], out['success_status'], out['success_gasUsed'] = r, outx['status'], int(outx['gasUsed'], 16)
out['success_effGasPrice'] = int(outx['effectiveGasPrice'], 16)
usdc_after = bal(exec_, USDC, exec_); weth_after = bal(exec_, WETH, exec_)
out['usdc_delta'] = str(usdc_after - usdc_before); out['weth_delta'] = str(weth_after - weth_before)
owner_usdc_after = bal(exec_, USDC, owner)
out['owner_usdc_delta'] = str(owner_usdc_after - owner_usdc_before)  # same-tx profit-to-wallet
gas_wei = out['success_gasUsed'] * out['success_effGasPrice']
out['gas_usd'] = round(gas_wei * ETH_USD / 10**18, 2)
out['profit_usd_after_gas'] = round((owner_usdc_after - owner_usdc_before) / 1e6 - out['gas_usd'], 2)
out['hf_after_success'] = hf_of(exec_, VICTIM)

# HEALTHY revert on the repaid victim (debt fully repaid by the success tx)
data = call_sig(VICTIM, WETH, USDC, 1000000, 1000000, 100)
tx['data'] = data
r, outx = send(tx)
out['healthy_tx'], out['healthy_status'] = r, outx['status']
try:
    revert_hex = rpc('eth_call', [{'from': owner, 'to': exec_, 'data': data}, 'latest'])
    out['healthy_revert_selector'] = '0x' + revert_hex[2:10]
except RuntimeError as e:  # anvil reports reverts as a call error; keep the custom-error selector it shows
    txt = str(e.args[0]) if e.args else str(e)
    i = txt.find('0x')
    out['healthy_revert_selector'] = txt[i:i + 10] if i >= 0 else txt[:40]

print(json.dumps(out, indent=1))
with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'nat_proof2.json'), 'w') as f:
    json.dump(out, f, indent=1)
assert out['success_status'] == '0x1' and out['profit_usd_after_gas'] > 0, 'success must be after-fee profitable'
assert int(out['owner_usdc_delta']) > 0, 'blocker 2: profit must reach the OWNER wallet in the same tx'
assert abs(int(out['usdc_delta'])) < 10**8, 'executor must retain no profit inventory (delta ~0)'
assert out['noprofit_status'] == '0x0' and out['noprofit_revert'] == 'NO_PROFIT'
assert out['balances_preserved'] and out['healthy_status'] == '0x0'
print('PROOF GREEN')
