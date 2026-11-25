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
 (26301940,'0x33ba32b6268c360a62f2aa0444eb438640ed3875','0x37c554a104fe58f9a51e50b3cdb7df1afa0283457468c62b40d33d0d702212d9'),
 (26301940,'0x208f09ff19fd7bc0c5fa47afda47ca62adfaa329','0x37c554a104fe58f9a51e50b3cdb7df1afa0283457468c62b40d33d0d702212d9'),
 (26300887,'0xfaf529343b99db2f8b640fc2e6b7e67b9a01c131','0x09aa78f18268b32e58b19294aba4ccd23fd5b0887ab1a3ef50f21f7fb8d7d042'),
 (26300860,'0x99da8b0cae360df0c2f1f855b8407ef69462e5f8','0x13a4cf9852a035266ca1edcc6ceac3d4fdbfdfe25326430008fa5dccc62580bf'),
]
out={}
for b,u,tx in cands:
    rx=rpc('eth_getTransactionReceipt',[tx])
    gas=int(rx['gasUsed'],16); fee=int(rx['effectiveGasPrice'],16)
    hfs={}
    for off in (1,100,500,1500,3000):
        try: hfs[off]=hf(u,b-off)
        except Exception as e: hfs[off]=str(e)[:60]
    blk=rpc('eth_getBlockByNumber',[hex(b-1),False])
    base=int(blk['baseFeePerGas'],16) if blk.get('baseFeePerGas') else None
    ts=int(blk['timestamp'],16)
    print(json.dumps(dict(block=b,user=u[:10],hf_by_parent_offset=hfs,winner_gas=gas,winner_effFeeWei=fee,era_baseFee=base,parent_ts=ts)))
