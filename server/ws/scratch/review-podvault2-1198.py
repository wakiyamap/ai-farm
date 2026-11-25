import json
import pathlib

source = pathlib.Path('/srv/farm/ws/scratch/trial-podvault2-base/proof.py').read_text()
namespace = {'__name__': 'proof_constants', '__file__': '/srv/farm/ws/scratch/trial-podvault2-base/proof.py'}
exec(source.split("run('fork', 'lease', CHAIN, '15'", 1)[0], namespace)

run = namespace['run']
cast = namespace['CAST']
chain = namespace['CHAIN']
owner = namespace['OWNER']
vault = namespace['VAULT']
weth = namespace['WETH']
artifact = namespace['ARTIFACT']
calldata = namespace['calldata']
send = namespace['send']
native = namespace['native']
bal = namespace['bal']
revert_output = namespace['revert_output']

run('fork', 'lease', chain, '8', 'independent paper review 1198')
try:
    run('fork', 'reset', chain, '59104694')
    args = run(cast, 'abi-encode', 'constructor(address)', owner)
    deployed = run('fork', 'deploy', chain, artifact, '--args', args)
    import re
    address = re.search(r'0x[0-9a-fA-F]{40}', deployed).group(0)
    run('fork', 'fund', chain, owner, '1')
    amount = 5 * 10**15
    before = native(owner)
    guarded = send(owner, address, calldata('ohm_fwd', amount, 10**18))
    after_guard = native(owner)
    success = send(owner, address, calldata('ohm_fwd', amount, 1))
    after_success = native(owner)
    result = {
        'deployed': address,
        'guard': {'hash': guarded['transactionHash'], 'status': guarded['status'],
                  'revert': revert_output(guarded['transactionHash']),
                  'owner_native_delta_wei': after_guard - before},
        'success': {'hash': success['transactionHash'], 'status': success['status'],
                    'gas_used': int(success['gasUsed'], 16),
                    'owner_native_delta_wei': after_success - after_guard},
        'executor_native_wei': native(address),
        'executor_weth_wei': bal(weth, address),
    }
    print(json.dumps(result, indent=2), flush=True)
finally:
    run('fork', 'release', chain, check=False)
