import json
import subprocess
from pathlib import Path

root = Path('/srv/farm/ws')
owner = '0xfffffffffffffffffffffffffffffffffffffffe'
manifest = (root / 'bots/paper/morpho-watcher-ethereum/manifest.yaml').read_text()
import yaml
m = yaml.safe_load(manifest)
artifact = str(root / m['executor'])
args = m['executor_args']

def fork(*argv):
    p = subprocess.run(['fork', *argv], cwd=root, text=True, capture_output=True)
    if p.returncode:
        raise RuntimeError('fork ' + ' '.join(argv[:3]) + ': ' + p.stdout[-500:] + p.stderr[-500:])
    return p.stdout.strip()

fork('lease', 'ethereum-review', '15', 'review 7cbf morpho')
try:
    fork('reset', 'ethereum-review', '26328589')
    fork('fund', 'ethereum-review', owner, '2')
    deployed = fork('deploy', 'ethereum-review', artifact, owner, '--args', args)
    print('deployed', deployed, flush=True)
    if '0xb464f7314d55ec6a9a0cf6f7f6df17af8ed5b352' not in deployed.lower():
        raise RuntimeError('deployed address differs from bot proof address')
    p = subprocess.run(['node', str(root / 'scratch/review-962b34af/morpho-proof.js')], cwd=root, text=True, capture_output=True)
    print(p.stdout, p.stderr, flush=True)
    if p.returncode:
        raise RuntimeError('morpho proof failed')
finally:
    fork('release', 'ethereum-review')
