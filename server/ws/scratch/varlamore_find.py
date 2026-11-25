import json
import subprocess
from concurrent.futures import ThreadPoolExecutor

logs = json.load(open('scratch/varlamore-factory-logs.json'))['result']
vaults = [x['topics'][1][-40:] for x in logs]

def owner(vault):
    addr = '0x' + vault
    args = json.dumps([{'to': addr, 'data': '0x8da5cb5b'}, 'latest'])
    p = subprocess.run(['python3', '/srv/farm/ws/tools/rpc.py', 'ethereum', 'eth_call', args], capture_output=True, text=True)
    try:
        data = json.loads(p.stdout)
        return addr, '0x' + data['result'][-40:]
    except Exception:
        return addr, 'ERROR ' + p.stdout[:100] + p.stderr[:100]

with ThreadPoolExecutor(max_workers=4) as pool:
    results = list(pool.map(owner, vaults))
for v, o in results:
    print(v, o)
