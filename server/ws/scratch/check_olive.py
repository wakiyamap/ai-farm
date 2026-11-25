import json
import re
import subprocess
from pathlib import Path

adapter = Path('scratch/olive-adapter.js').read_text().split('arbitrum:')[0]
addresses = list(dict.fromkeys(re.findall(r'0x[a-fA-F0-9]{40}', adapter)))
for address in addresses:
    results = []
    for method, params in [
        ('eth_getCode', [address, 'latest']),
        ('eth_call', [{'to': address, 'data': '0xf53d0a8e' if address.lower() == '0xd94a9fbae86e662350ffebb352f70c3cbeb9e96e' else '0xfc0c546a'}, 'latest']),
    ]:
        p = subprocess.run(['python3', 'tools/rpc.py', 'ethereum', method, json.dumps(params)], capture_output=True, text=True)
        try:
            result = json.loads(p.stdout).get('result')
        except json.JSONDecodeError:
            result = None
        results.append(bool(result and result != '0x'))
    print(address, 'code=' + str(results[0]), 'getter=' + str(results[1]), flush=True)
