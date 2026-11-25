import json, urllib.request
RELAY='http://127.0.0.1:8545/ethereum?lane=research'
POOL='0x87870bca3f3fd6335c3f4ce8392d69350b4fa4e2'
def rpc(method, params):
    p={'jsonrpc':'2.0','id':1,'method':method,'params':params}
    req=urllib.request.Request(RELAY, json.dumps(p).encode(), {'content-type':'application/json'})
    r=json.loads(urllib.request.urlopen(req, timeout=90).read())
    if 'error' in r: raise RuntimeError(f'{method}: {r["error"]}')
    return r['result']
def pad(a): return a[2:].lower().rjust(64,'0')
def hf(user, block):
    hexs=rpc('eth_call',[{'from':'0x34652045730663d74b7ce034324e4ebcee389d01','to':POOL,'data':'0xbf92857c'+pad(user)}, hex(block)])
    return int(hexs[2:][5*64:6*64],16)/1e18
cands=[
 (26194899,'0x99da8b0cae360df0c2f1f855b8407ef69462e5f8','0xfef7e75a5502a12889c96bac94c6eb6a4dac7254217b00632ec89da6b019a53e'),
 (26194899,'0x7baecee44f3f1af9a9d8a0535be0f47b58a7383d','0xfef7e75a5502a12889c96bac94c6eb6a4dac7254217b00632ec89da6b019a53e'),
 (26194909,'0xc8097d434b46888a14be77dfc836d86971e3c40f','0x6c85e8b6206111a6233160cfe92b3416ef93f00f5863e22366a76f062f8abd68'),
 (26194929,'0xd12a16aaa884eb84303074811001b8eb087ead3c','0xf25358f812f68d7bd87e6b1f571a1e92a03c0ad7377318f7394fac8559efa384'),
 (26220060,'0x34cbae0e0c9b19e3d40814593dd49d39aebbe214','0x5595ded83a67baf974c1866901a440d4f840b73805d149fc1222da7995921b02'),
 (26248076,'0x9f36f1f3b3dbf1939f318cd97d9412f056255c83','0x0f41c4143e965fe9c26509f976cf31374460f6899ee796966a4b65b110e9aa2f'),
 (26248379,'0x0ca643f8e9d80fcc59e6595abf3ba42a4e616f11','0xeb7833abff05f15b7c6395a831144b9a736f1242be25830a37e6eb2a1929ffe6'),
 (26263314,'0x6544f40f825885431c943819c251d6eb52c803e2','0x81409c105eec7226a528e3a611e9c67e0f0eb8f6c5a719a387c013cac0614b68'),
 (26263314,'0xc2f590e3e340ae550324a256f3c3489ad7e65541','0x81409c105eec7226a528e3a611e9c67e0f0eb8f6c5a719a387c013cac0614b68'),
 (26263347,'0x50873a46c41d005c5a9f0e9e1403c3307d6209ab','0xb20c17da19857f1b69f6d84f7d0cc9c55877f4e6830017812f3a4bd9549527f5'),
]
res=[]
for b,u,tx in cands:
    rx=rpc('eth_getTransactionReceipt',[tx])
    if rx is None: gas=fee=None
    else: gas=int(rx['gasUsed'],16); fee=int(rx['effectiveGasPrice'],16)
    hfs={}
    for off in (1,100,500,1500):
        try: hfs[off]=round(hf(u,b-off),6)
        except Exception as e: hfs[off]=str(e)[:50]
    blk=rpc('eth_getBlockByNumber',[hex(b-1),False])
    base=int(blk['baseFeePerGas'],16) if blk.get('baseFeePerGas') else None
    ts=int(blk['timestamp'],16)
    row=dict(block=b,user=u[:10],hf=hfs,winner_gas=gas,winner_fee=fee,era_base=base,parent_ts=ts)
    res.append(row); print(json.dumps(row))
json.dump(res, open('scratch/cand_windows.json','w'))
