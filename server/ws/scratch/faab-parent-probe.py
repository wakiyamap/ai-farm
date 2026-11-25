"""Classify whether sampled Base Morpho captures were takeable at parent block."""
import json
import subprocess
from pathlib import Path

ROOT = Path('/srv/farm/ws')
CAST = '/opt/foundry/bin/cast'
RPC = '/srv/farm/ws/tools/rpc.py'
MORPHO = '0xBBBBBbbBBb9cC5e90e3b3Af64bdAF62C37EEFFCb'
MP = '(0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913,0xcbB7C0000aB88B473b1f5aFd9ef808440eed33Bf,0x663BECd10daE6C4A3Dcd89F1d76c1174199639B9,0x46415998764C29aB2a25CbeA6254146D50D22687,860000000000000000)'
SIG = 'liquidate((address,address,address,address,uint256),address,uint256,uint256,bytes)'
FROM = '0xc0ffee0000000000000000000000000000000001'
CASES = [
    (60257174, '0xf47ad0b7bd3fecd72860dae892245a56614c4cbb', 59834079934146, '0x8ae2395f93d846a90baff67a874461ac505e5ffb3a1e461750d015d0e1bddeee'),
    (60218594, '0x36c3d41e3264647c34568e2a97c4bb6e8b4a2fab', 4608210070307, '0x3d7317ed24739620de13ad84b4a9063fcd10ef1f52ef865e76ba68b659e5d797'),
    (60218448, '0x4db267628e8763a00260c0e5d985dc58c9cb3b34', 2160901702904190, '0xfb0a877c792b85a58c338b80ac1ecdcd333deffbd52d5e922f28cd050a058ccd'),
    (60217553, '0xcdff233661ea431044b2868b49989498149eebbf', 8286984449894277, '0x7985c0f1c327e012d96387f1ca7d21ee45d8d2ea43e1185e8be93fcce48251e4'),
    (57583736, '0xd62debfd1547330f390d310b3d1c21f908081233', 24670345777030, '0x7f3e5b9ba0')
]

def call(args):
    p = subprocess.run(args, cwd=ROOT, text=True, capture_output=True)
    return {'exit': p.returncode, 'stdout': p.stdout.strip(), 'stderr': p.stderr.strip()}

rows = []
for block, borrower, shares, txhash in CASES:
    enc = call([CAST, 'calldata', SIG, MP, borrower, '0', str(shares), '0x'])
    if enc['exit']:
        raise RuntimeError(enc)
    data = enc['stdout']
    for delta in (1, 2, 16):
        params = [{'from': FROM, 'to': MORPHO, 'data': data}, hex(block-delta)]
        result = call(['python3', RPC, 'base', 'eth_call', json.dumps(params)])
        rows.append({'capture_block': block, 'probe_block': block-delta, 'borrower': borrower,
                     'txhash': txhash, 'request': params, 'response': result})
    print(block, borrower, [r['response']['stderr'][-100:] or r['response']['stdout'][-100:] for r in rows[-3:]], flush=True)

out = ROOT / 'scratch/faab-parent-probe.json'
out.write_text(json.dumps(rows, indent=2) + '\n')
print(out)
