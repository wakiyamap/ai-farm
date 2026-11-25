import json, urllib.request, os, subprocess
URL=os.environ['RPC_RELAY_URL']
def rpc(method, params, chain='ethereum', lane='research'):
    body=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    req=urllib.request.Request(f"{URL}/{chain}?lane={lane}", data=body, headers={'content-type':'application/json'})
    d=json.loads(urllib.request.urlopen(req, timeout=60).read())
    return d.get('result', 'ERR:'+str(d.get('error',{}).get('message')))
os.environ['PATH']='/opt/foundry/bin:'+os.environ['PATH']
def sel(sig): return '0x'+subprocess.run(['cast','keccak',sig],capture_output=True,text=True).stdout.strip().replace('0x','')[:8]
def call(to,g):
    return rpc("eth_call",[{"to":to,"data":sel(g)},"latest"])
def addr(v): return "0x"+v[-40:] if isinstance(v,str) and v.startswith('0x000000000000000000000000') else v
DISTRO="0xd16d5ec345dd86fb63c6a9c43c517210f1027914"
print('feeDistro name() ->', call(DISTRO,'name()'), 'ctrl')
print('feeDistro vlcvx() ->', addr(call(DISTRO,'vlcvx()')))
print('feeDistro totalSupply() ->', call(DISTRO,'totalSupply()'))
for g in ['getForLockers(address)','distributionsFeesActive()','distributionsIncentive()','lockers(uint256)','getVaultBalance()','feesDashboard()']:
    print('feeDistro', g, '->', call(DISTRO,g))
