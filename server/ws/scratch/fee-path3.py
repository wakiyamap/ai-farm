import json, urllib.request, os, subprocess
URL=os.environ['RPC_RELAY_URL']
def rpc(method, params, chain='ethereum', lane='research'):
    body=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    req=urllib.request.Request(f"{URL}/{chain}?lane={lane}", data=body, headers={'content-type':'application/json'})
    d=json.loads(urllib.request.urlopen(req, timeout=60).read())
    return d.get('result', 'ERR:'+str(d.get('error',{}).get('message')))
os.environ['PATH']='/opt/foundry/bin:'+os.environ['PATH']
def sel(sig): return '0x'+subprocess.run(['cast','keccak',sig],capture_output=True,text=True).stdout.strip().replace('0x','')[:8]
def call(to,g): return rpc("eth_call",[{"to":to,"data":sel(g)},"latest"])
def addr(v): return "0x"+v[-40:] if isinstance(v,str) and v.startswith('0x000000000000000000000000') else v
BOOST="0xf403c135812408bfbe8713b5a23a04b3d48aae31"
REG=addr(call(BOOST,'feeManager()')); print('feeManager ->', REG, 'ctrl: registry totalFees() ->', call(REG,'totalFees()'))
FD=addr(call(REG,'feeDeposit()')); print('registry feeDeposit() ->', FD)
print('live FeeDeposit vlcvx() ->', addr(call(FD,'vlcvx()')), 'ctrl minter() ->', call(FD,'minter()')[:42])
VLC=addr(call(FD,'vlcvx()'))
if VLC and VLC.startswith('0x'):
    for g in ['name()','totalSupply()','symbol()','getForLockers(address)','distributionsFeesActive()','distributionsIncentive()','lockers(uint256)']:
        print('vlcvx', g, '->', call(VLC,g))
