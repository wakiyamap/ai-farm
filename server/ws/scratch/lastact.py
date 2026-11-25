import json, subprocess
def rpc(method, params):
    out = subprocess.run(['python3','/srv/farm/ws/tools/rpc.py','ethereum',method,json.dumps(params)],
                         capture_output=True, text=True).stdout
    d = json.loads(out)
    if 'error' in d: raise SystemExit(str(d['error'])[:200])
    return d['result']
# vault: last activity in ~90 days (blocks 23.3M back is too far; use 90d ~ 664k blocks)
V='0x131fb74c6fede6d6710ff224e07ce0ed8123f144'
latest=26465298
fromB=latest-664000
logs=rpc('eth_getLogs',[{'address':V,'fromBlock':hex(fromB),'toBlock':hex(latest)}])
print('vault logs in ~90d:',len(logs))
for l in logs[-5:]:
    b=rpc('eth_getBlockByNumber',[hex(int(l['blockNumber'],16)),False])
    print(l['blockNumber'], l['transactionHash'][:20], l['topics'][0][:18], __import__('datetime').datetime.utcfromtimestamp(int(b['timestamp'],16)).isoformat())
