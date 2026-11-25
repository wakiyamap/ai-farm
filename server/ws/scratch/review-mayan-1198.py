import json
import pathlib

source = pathlib.Path('/srv/farm/ws/scratch/trial-mayan-redeem-arbitrum/proof.py').read_text()
namespace = {'__name__': 'proof_constants', '__file__': '/srv/farm/ws/scratch/trial-mayan-redeem-arbitrum/proof.py'}
exec(source.split("run('fork', 'lease', CHAIN, '15'", 1)[0], namespace)

run = namespace['run']
cast = namespace['CAST']
chain = namespace['CHAIN']
owner = namespace['OWNER']
usdc = namespace['USDC']
fee_mgr = namespace['FEEMGR']
artifact = namespace['ARTIFACT']
calldata = namespace['calldata']
fee = namespace['fee']
send = namespace['send']
native = namespace['native']
bal = namespace['bal']
revert_output = namespace['revert_output']
parent = namespace['parent']

run('fork', 'lease', chain, '8', 'independent paper review 1198')
try:
    run('fork', 'reset', chain, str(parent))
    args = run(cast, 'abi-encode', 'constructor(address)', owner)
    deployed = run('fork', 'deploy', chain, artifact, '--args', args)
    import re
    address = re.search(r'0x[0-9a-fA-F]{40}', deployed).group(0)
    run('fork', 'fund', chain, owner, '1')
    before_native, before_usdc = native(owner), bal(usdc, owner)
    guarded = send(owner, address, calldata(fee + 1))
    after_guard_native, after_guard_usdc = native(owner), bal(usdc, owner)
    success = send(owner, address, calldata(fee))
    after_success_native, after_success_usdc = native(owner), bal(usdc, owner)
    credit = int(run(cast, 'call', fee_mgr, 'getRelayerFee(address,address)(uint256)', address, usdc,
                     '--rpc-url', namespace['URL']).split()[0])
    result = {
        'parent': parent, 'deployed': address, 'redeem_fee_usdc_units': fee,
        'guard': {'hash': guarded['transactionHash'], 'status': guarded['status'],
                  'revert': revert_output(guarded['transactionHash']),
                  'owner_native_delta_wei': after_guard_native - before_native,
                  'owner_usdc_delta': after_guard_usdc - before_usdc},
        'success': {'hash': success['transactionHash'], 'status': success['status'],
                    'gas_used': int(success['gasUsed'], 16),
                    'owner_native_delta_wei': after_success_native - after_guard_native,
                    'owner_usdc_delta': after_success_usdc - after_guard_usdc},
        'executor_native_wei': native(address), 'executor_usdc_units': bal(usdc, address),
        'fee_manager_credit_units': credit,
    }
    print(json.dumps(result, indent=2), flush=True)
finally:
    run('fork', 'release', chain, check=False)
