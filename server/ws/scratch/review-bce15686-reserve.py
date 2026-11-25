import json
import subprocess

CHAIN = 'ethereum'
ROOT = '/srv/farm/ws/scratch/reserve-bot/contracts'
OWNER = '0x0d0e000000000000000000000000000000000d0e'
TRADE = '0x527DC250356C8833CD5e2856Dd617dd400Cf9257'
ETHP = '0xE72B141DF173b999AE7c1aDcbF60Cc9833Ce56a8'

def run(*args):
    p = subprocess.run(args, capture_output=True, text=True, check=True)
    return p.stdout.strip()

def fork(*args):
    return run('fork', *args)

def calldata(sig, *args):
    return run('/opt/foundry/bin/cast', 'calldata', sig, *(str(a) for a in args))

def send(to, data):
    out = fork('send', CHAIN, json.dumps({'from': OWNER, 'to': to, 'input': data, 'gas': '0x200000'}))
    return json.loads(out[out.index('{'):out.rindex('}') + 1])

def balance(addr):
    out = fork('call', CHAIN, json.dumps({'from': OWNER, 'to': ETHP,
                                         'input': calldata('balanceOf(address)', addr)}))
    return int(out.splitlines()[-1], 16)

artifact = json.load(open(ROOT + '/out/ReserveDutch.sol/ReserveDutch.json'))
bytecode = artifact['bytecode']['object'] + '0' * 128
bytecode_file = '/srv/farm/ws/scratch/review-bce15686-reserve.hex'
open(bytecode_file, 'w').write(bytecode)
fork('lease', CHAIN, '5', 'paper-reviewer guard-before-success')
try:
    fork('reset', CHAIN, '26348315')
    fork('fund', CHAIN, OWNER, '2')
    contract = fork('deploy', CHAIN, bytecode_file, OWNER).splitlines()[-1]
    pre = balance(contract)
    guard = send(contract, calldata('bidDutch(address,address,uint256)', TRADE, ETHP, 10**27))
    post_guard = balance(contract)
    trace = json.loads(fork('trace', CHAIN, guard['transactionHash']))
    success = send(contract, calldata('bidDutch(address,address,uint256)', TRADE, ETHP, 1))
    post_success = balance(contract)
    print(json.dumps({'pre_balance': pre, 'guard_status': guard['status'],
                      'guard_revert_reason': trace.get('revertReason'),
                      'post_guard_balance': post_guard, 'success_status': success['status'],
                      'post_success_balance': post_success, 'success_gas_used': success['gasUsed'],
                      'guard_tx': guard['transactionHash'], 'success_tx': success['transactionHash']}, indent=2))
finally:
    fork('release', CHAIN)
