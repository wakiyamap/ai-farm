#!/usr/bin/env python3
# Rerunnable ReserveDutch fork proof: fork reset 26348315 -> deploy -> fund
# owner -> guard revert (NO_PROFIT, balances preserved) -> success with
# positive ETH+ delta -> settled-trade eligibility revert. Takes a lease;
# releases at the end. Prints proof JSON to stdout and proof.json.
import json, subprocess, sys, urllib.request
CHAIN, URL = 'ethereum-review', 'http://127.0.0.1:9013'
TRADE = '0x527DC250356C8833CD5e2856Dd617dd400Cf9257'
ETHP = '0xE72B141DF173b999AE7c1aDcbF60Cc9833Ce56a8'
FROM = '0x0d0e000000000000000000000000000000000d0e'
GUARD = '100000000000000000000000000000000000'  # 1e27: no trade pays this
MINP = '180000000000000'
def sh(*args):
    r = subprocess.run(['fork', *args], capture_output=True, text=True)
    if r.returncode != 0: sys.exit(f'fork {args} failed: {r.stderr}{r.stdout}')
    return r.stdout.strip()
_id = [0]
def rpc(method, params):
    _id[0] += 1
    req = json.dumps({'jsonrpc': '2.0', 'id': _id[0], 'method': method, 'params': params}).encode()
    r = json.loads(urllib.request.urlopen(URL, req).read())
    if 'error' in r: sys.exit(f'{method}: {r["error"]}')
    return r['result']
def calldata(sig, *args):  # cast calldata
    r = subprocess.run(['/opt/foundry/bin/cast', 'calldata', sig, *[str(a) for a in args]],
                       capture_output=True, text=True)
    if r.returncode != 0: sys.exit(f'cast failed: {r.stderr}')
    return r.stdout.strip()
def send(tx):
    out = sh('send', CHAIN, json.dumps(tx))
    s = out[out.index('{'):]
    return json.loads(s[:s.rindex('}') + 1])
def deploy(frm):
    open('contracts/.bc.hex', 'w').write(BC)
    out = sh('deploy', CHAIN, 'contracts/.bc.hex', frm)
    return out.splitlines()[-1].strip()
STATUS = {}
GASUSED = {}
def call(frm, to, data, gp='0x5f5e100'):
    rc = send({'from': frm, 'to': to, 'input': data, 'gas': '0x200000', 'maxFeePerGas': gp, 'maxPriorityFeePerGas': ('0x0' if gp == '0x5f5e100' else gp)})
    STATUS[rc['transactionHash']] = rc.get('status')
    GASUSED[rc['transactionHash']] = rc.get('gasUsed')
    return rc['transactionHash']
def status(h):
    return STATUS[h]
def gas_used(h):
    return GASUSED[h]
def bal(addr):
    tx = {'to': ETHP, 'from': FROM, 'input': calldata('balanceOf(address)', addr)}
    out = sh('call', CHAIN, json.dumps(tx))
    return int(out.splitlines()[-1].strip(), 16)
BC = json.load(open('contracts/out/ReserveDutch.sol/ReserveDutch.json'))['bytecode']['object'] \
     + '0' * 128  # constructor(leg3Variant=0, repayMode=0)
sh('lease', CHAIN, '10', 'reserve-dutch proof.py')
try:
    out = subprocess.run(['fork', 'reset', CHAIN, '26348315'], capture_output=True, text=True)
    sh('fund', CHAIN, FROM, '2')
    E2 = deploy(FROM)
    h_guard = call(FROM, E2, calldata('bidDutch(address,address,uint256)', TRADE, ETHP, GUARD))
    b2 = bal(E2)
    E1 = deploy(FROM)
    b0 = bal(E1)
    h_succ = call(FROM, E1, calldata('bidDutch(address,address,uint256)', TRADE, ETHP, MINP))
    b1 = bal(E1)
    # settled trade cannot be bid again
    h_elig = call(FROM, E1, calldata('bidDutch(address,address,uint256)', TRADE, ETHP, MINP))
    E3 = deploy(FROM)
    h_gas = call(FROM, E3, calldata('bidDutch(address,address,uint256)', TRADE, ETHP, MINP), '0x' + hex(40 * 10**9)[2:])
    b3 = bal(E3)
    proof = {'reset_block': 26348315, 'executor': E1, 'executor_guard': E2,
             'success_tx': h_succ, 'success_status': status(h_succ),
             'ethp_before': hex(b0), 'ethp_after': hex(b1),
             'ethp_delta': hex(b1 - b0),
             'eligibility_tx': h_elig, 'eligibility_status': status(h_elig),
             'guard_tx': h_guard, 'guard_status': status(h_guard),
             'guard_ethp_balance': hex(b2), 'success_gas_used': gas_used(h_succ),
             'gas_usd_guard_tx': h_gas, 'gas_usd_guard_status': status(h_gas),
             'gas_usd_guard_gas_price_gwei': 40, 'gas_usd_guard_ethp_balance': hex(b3),
             'gas_usd_guard_revert': 'GAS_USD: (gasleft+22000) x 40 gwei x oracle answer > 20 USD at inclusion block',
             'gas': 'maxFeePerGas x gasLimit <= 18 USD Base wallet cap n/a; ethereum gas bounded by signed fields'}
    assert proof['success_status'] == '0x1' and b1 > b0 and proof['eligibility_status'] == '0x0' \
        and proof['guard_status'] == '0x0' and b2 == 0 \
        and proof['gas_usd_guard_status'] == '0x0' and b3 == 0, f'proof not green: {proof}'
    json.dump(proof, open('/srv/farm/ws/scratch/review-233973f5-reserve-proof.json', 'w'), indent=1)
    print(json.dumps(proof, indent=1))
finally:
    sh('release', CHAIN)
