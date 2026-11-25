import json
import subprocess
from complifi_logs import vaults

def rpc(method, params):
    p = subprocess.run(['python3', '/srv/farm/ws/tools/rpc.py', 'ethereum', method,
                        json.dumps(params)], capture_output=True, text=True)
    try:
        return json.loads(p.stdout).get('result')
    except Exception:
        return None

for address in vaults:
    code = rpc('eth_getCode', [address, 'latest'])
    state = rpc('eth_call', [{'to': address, 'data': '0xc19d93fb'}, 'latest'])
    print(address, 'code_bytes', (len(code) - 2)//2 if code else None,
          'state', int(state, 16) if state else None)
