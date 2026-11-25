import subprocess, json
toks = {'USDC':'0xaf88d065e77c8cc2239327c5edb3a432268e5831','USDT0':'0x0b6eac11aad4211ad686d1ece56c071e306bd29b',
        'WETH':'0x82af49447d8a07e3bd95bd0d56f35241523fbab1','WBTC':'0x2f2a2543b76a4166549f7aa2723360bc825d4bab',
        'wstETH':'0x5979d7b546e38e414a7e982f97b64ee5bc08e77c'}
acc='0xf399972cff76e258175e4fc9e2f5cc24bebd0cc1'
def call(to,data,blk):
    p=subprocess.run(['python3','tools/rpc.py','arbitrum','eth_call',json.dumps([{'to':to,'data':data},hex(blk)]),'--lane','research'],capture_output=True,text=True)
    try: return int(json.loads(p.stdout)['result'],16)
    except Exception: return None
def bal(tok,blk):
    if tok=='ETH':
        p=subprocess.run(['python3','tools/rpc.py','arbitrum','eth_getBalance',json.dumps([acc,hex(blk)]),'--lane','research'],capture_output=True,text=True)
        return int(json.loads(p.stdout)['result'],16)
    return call(toks[tok],'0x70a08231'+acc[2:].zfill(64),blk)
txs=[('0x1dd189a3',524265641),('0xbf15e963',523745539),('0xbd1aa39b',524319771)]
for name,blk in txs:
    print(name)
    for t in ['ETH','USDC','USDT0','WETH','WBTC','wstETH']:
        b0=bal(t,blk-1); b1=bal(t,blk)
        if b0 is None or b1 is None: print('  ',t,'err'); continue
        d=(b1-b0)/1e18 if t in ('WETH','wstETH','ETH') else (b1-b0)/1e6 if t in ('USDC','USDT0') else (b1-b0)/1e8
        if abs(d)>1e-9: print('   %-7s delta %+.6f' % (t,d))
