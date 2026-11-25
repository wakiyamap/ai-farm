import json
import subprocess
from concurrent.futures import ThreadPoolExecutor

CASES = [
    ('BDP token code', 'eth_getCode', ['0xf3dcbc6d72a4e1892f7917b7c43b74131df8480e', 'latest']),
    ('BDP master code', 'eth_getCode', ['0x0De845955E2bF089012F682fE9bC81dD5f11B372', 'latest']),
    ('bALPHA token code', 'eth_getCode', ['0x7a5ce6abD131EA6B148a022CB76fc180ae3315A6', 'latest']),
    ('bALPHA master code', 'eth_getCode', ['0xf20084BA368567fa3dA1Da85b43Ac1AC310880C8', 'latest']),
    ('BDP master poolLength', 'eth_call', [{'to':'0x0De845955E2bF089012F682fE9bC81dD5f11B372','data':'0x081e3eda'}, 'latest']),
    ('bALPHA master poolLength', 'eth_call', [{'to':'0xf20084BA368567fa3dA1Da85b43Ac1AC310880C8','data':'0x081e3eda'}, 'latest']),
    ('BDP token seedPoolAmount', 'eth_call', [{'to':'0xf3dcbc6d72a4e1892f7917b7c43b74131df8480e','data':'0x75993783'}, 'latest']),
    ('bALPHA token cap', 'eth_call', [{'to':'0x7a5ce6abD131EA6B148a022CB76fc180ae3315A6','data':'0x355274ea'}, 'latest']),
    ('bALPHA token supply', 'eth_call', [{'to':'0x7a5ce6abD131EA6B148a022CB76fc180ae3315A6','data':'0x18160ddd'}, 'latest']),
    ('BDP token master', 'eth_call', [{'to':'0xf3dcbc6d72a4e1892f7917b7c43b74131df8480e','data':'0x52e2c41b'}, 'latest']),
    ('bALPHA token master', 'eth_call', [{'to':'0x7a5ce6abD131EA6B148a022CB76fc180ae3315A6','data':'0xc2344914'}, 'latest']),
]

def run(case):
    name, method, params = case
    p = subprocess.run(['python3','/srv/farm/ws/tools/rpc.py','ethereum',method,json.dumps(params)],capture_output=True,text=True)
    try:
        d = json.loads(p.stdout)
        v = d.get('result',d)
        if method == 'eth_getCode': v = 'code bytes: '+str((len(v)-2)//2) if isinstance(v,str) and v.startswith('0x') else v
        elif isinstance(v,str) and v.startswith('0x'): v = str(int(v,16))+' ('+v+')'
    except Exception: v = p.stdout.strip()
    return name, p.returncode, v, p.stderr.strip()

with ThreadPoolExecutor(max_workers=4) as pool:
    for row in pool.map(run,CASES): print(*row,sep=' | ')
