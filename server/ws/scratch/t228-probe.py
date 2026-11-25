import json,subprocess,sys,collections
def rpc(m,p):
    r=subprocess.run(['python3','/srv/farm/ws/tools/rpc.py','hyperevm',m,json.dumps(p)],capture_output=True,text=True)
    try: return json.loads(r.stdout)
    except Exception: return {'raw':r.stdout[:300],'err':r.stderr[:300]}
head=int(rpc('eth_blockNumber',[])['result'],16)
print('head',head)
for a in ['0x24c8964338deb5204b096039147b8e8c3aea42cc','0x131141e6c88a3389a4ab2368d3bbc65df1bf4a7e','0xa8a94da411425634e3ed6c331a32ab4fd774aa43','0x194fff37872bac3531a41fa5c426090ff84f4f31']:
    r=rpc('eth_getLogs',[{'address':a,'fromBlock':hex(head-900),'toBlock':hex(head)}])
    L=r.get('result')
    if L is None: print(a,r); continue
    c=collections.Counter(x['topics'][0] for x in L)
    print(a,len(L),dict(c), [int(x['blockNumber'],16) for x in L[-5:]])
    if L: print(json.dumps(L[-1])[:900])
# pool getters
for sel,name in [('0x0dfe1681','token0'),('0xd21220a7','token1'),('0xddca3f43','fee'),('0x3850c7bd','slot0'),('0x1a686502','liquidity')]:
    print(name, rpc('eth_call',[{'to':'0x6c9a33e3b592c0d65b3ba59355d5be0d38259285','data':sel},'latest']).get('result','ERR')[:200])
print('price194', rpc('eth_call',[{'to':'0x194fff37872bac3531a41fa5c426090ff84f4f31','data':'0xa035b1fe'},'latest']))
print('priceA6', rpc('eth_call',[{'to':'0xA6eCdF8CB132BFa50916A421d06bE41A57179dD9','data':'0xa035b1fe'},'latest']))
r=rpc('eth_getTransactionReceipt',['0x7bb3691a20c70e9f673afa3b5d898ac89b3b5e95ff78a2d0b8815c050db5f756'])['result']
print('winblock',int(r['blockNumber'],16),int(r['effectiveGasPrice'],16)/1e9)
