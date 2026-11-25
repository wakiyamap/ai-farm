import subprocess, json, sys
def rpc(method, params):
    r = subprocess.run(['python3','/srv/farm/ws/tools/rpc.py','arbitrum',method,json.dumps(params)], capture_output=True, text=True)
    out = json.loads(r.stdout)
    if 'error' in out: return {'ERR': out['error']}
    return out['result']
FRESH='0xB0b0C0FFee1c2d2c1D4a5E6f0b9E2cA7d3F1a2B3'
STK='0x48c81451d1fddeca84b47ff86f91708fa5c32e93'
V2='0x8080B5cE6dfb49a6B86370d6982B3e2A86FBBb08'
print('massUpdatePools fresh:', rpc('eth_call',[{'from':FRESH,'to':STK,'data':'0x630b5ba1'},'latest']))
print('deposit(0,0) fresh:', rpc('eth_call',[{'from':FRESH,'to':STK,'data':'0xe2bbb158'+ '0'*64*2},'latest']))
print('withdraw(0,0) fresh:', rpc('eth_call',[{'from':FRESH,'to':STK,'data':'0x441a3e70'+'0'*64*2},'latest']))
print('updateGLPbackingNeeded fresh:', rpc('eth_call',[{'from':FRESH,'to':V2,'data':'0x766dd4ca'},'latest']))
