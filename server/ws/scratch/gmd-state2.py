import subprocess, json
def rpc(method, params):
    r = subprocess.run(['python3','/srv/farm/ws/tools/rpc.py','arbitrum',method,json.dumps(params)], capture_output=True, text=True)
    out = json.loads(r.stdout)
    if 'error' in out: return {'ERR': out['error']}
    return out['result']
STK='0x48c81451d1fddeca84b47ff86f91708fa5c32e93'
WETH='0x82aF49447D8a07e3bd95BD0d56f35241523fBab1'
DEP='0xf02dea93d2beab2116b224d4e0d5cd141d8ec1a2'
sel = {name: subprocess.run(['cast','sig',sig],capture_output=True,text=True).stdout.strip() for name,sig in
       [('withdrawable','withdrawable()'),('poolLength','poolLength()'),('WETHPerSecond','WETHPerSecond()'),('RPPerSecond','RPPerSecond()'),('pendingWETH','pendingWETH(uint256,address)')]}
def call(to,s,arghex=''):
    return rpc('eth_call',[{'to':to,'data':s+arghex},'latest'])
print('withdrawable:', call(STK,sel['withdrawable']))
pl=int(call(STK,sel['poolLength']),16); print('poolLength:', pl)
print('WETHPerSecond:', int(call(STK,sel['WETHPerSecond']),16)/1e18)
print('RPPerSecond:', int(call(STK,sel['RPPerSecond']),16)/1e18)
print('WETH bal staking (WETH):', int(rpc('eth_call',[{'to':WETH,'data':'0x70a08231'+'0'*24+STK[2:]},'latest']),16)/1e18)
for pid in range(min(pl,3)):
    p=call(STK,sel['pendingWETH'],hex(pid)[2:].rjust(64,'0')+'0'*24+DEP[2:])
    print(f'pendingWETH(pid={pid}, depositor 0xf02d):', int(p,16)/1e18 if isinstance(p,str) else p)
