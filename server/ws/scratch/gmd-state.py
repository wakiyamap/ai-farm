import subprocess, json
def rpc(method, params):
    r = subprocess.run(['python3','/srv/farm/ws/tools/rpc.py','arbitrum',method,json.dumps(params)], capture_output=True, text=True)
    out = json.loads(r.stdout)
    if 'error' in out: return {'ERR': out['error']}
    return out['result']
STK='0x48c81451d1fddeca84b47ff86f91708fa5c32e93'
WETH='0x82aF49447D8a07e3bd95BD0d56f35241523fBab1'
print('withdrawable:', rpc('eth_call',[{'to':STK,'data':'0x492c8cd6'},'latest']))  # withdrawable()
print('poolLength:', int(rpc('eth_call',[{'to':STK,'data':'0x8f32c412'},'latest']),16))
print('WETHPerSecond:', int(rpc('eth_call',[{'to':STK,'data':'0x26287eb6'},'latest']),16))
print('WETH bal of staking:', int(rpc('eth_call',[{'to':WETH,'data':'0x70a08231'+'0'*24+STK[2:]},'latest']),16)/1e18)
print('totalWETHdistributed:', int(rpc('eth_call',[{'to':STK,'data':'0x25f5fa67'},'latest']),16)/1e18)
