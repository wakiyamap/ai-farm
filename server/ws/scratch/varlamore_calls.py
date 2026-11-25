import json
import subprocess
from concurrent.futures import ThreadPoolExecutor

vaults = ['0xd6b1d1fc1531046b1af598cc9d06d005659a13e9', '0xa9b23b28621cfb32e0ebf50b572afac671fcc17b', '0xb4b98983ad44257e267f5bdd3b4a86fb40e2ee5f', '0xad43bd27a4d7c18c05f78f24d9bd3fa6805c2ff6']
def call(pair):
    vault, data = pair
    args = json.dumps([{'from':'0x000000000000000000000000000000000000dEaD','to':vault,'data':data},'latest'])
    p = subprocess.run(['python3','/srv/farm/ws/tools/rpc.py','ethereum','eth_call',args],capture_output=True,text=True)
    return vault, data, p.stdout.strip()[:300], p.stderr.strip()[:100]
with ThreadPoolExecutor(max_workers=4) as pool:
    result = list(pool.map(call, [(v,d) for v in vaults for d in ['0xfadbdada']]))
for x in result: print(*x)
