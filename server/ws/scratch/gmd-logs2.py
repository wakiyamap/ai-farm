import subprocess, json
def rpc(method, params=[]):
    r = subprocess.run(['python3','/srv/farm/ws/tools/rpc.py','arbitrum',method,json.dumps(params)], capture_output=True, text=True)
    out = json.loads(r.stdout)
    if 'error' in out: return {'ERR': out['error']}
    return out['result']
STK='0x48c81451d1fddeca84b47ff86f91708fa5c32e93'
DEP_T='0x90890809c654f11d6e72a28fa60149770a0d11ec6c92319d6ceb2bb0a4ea1a15'
WDR_T='0xf279e6a1f5e320cca91135676d9cb6e44ca8a08c0b88342bcdb1144f6511b568'
last=int(rpc('eth_blockNumber'),16)
r=rpc('eth_getLogs',[{'fromBlock':hex(523480000),'toBlock':hex(last),'address':STK,'topics':[[DEP_T,WDR_T]]}])
print('staking Deposit|Withdraw last 7d (block 523480000..%d):'%last, len(r) if isinstance(r,list) else r)
r2=rpc('eth_getLogs',[{'fromBlock':hex(514020000),'toBlock':hex(514030000),'address':STK,'topics':[[DEP_T,WDR_T]]}])
print('CONTROL Oct12 same shape:', len(r2) if isinstance(r2,list) else r2)
print('gasPrice wei:', int(rpc('eth_gasPrice'),16))
