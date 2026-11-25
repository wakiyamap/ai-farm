import json, urllib.request, sys
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
 (26302299,'0xbf0fc547a8624a8540e99c8dc434e464e171f598','0xd9994fea36a57fcb52d4c31c2325e394a79cef8af42e10514277d3961fc5593b'),
 (26302299,'0x56cc773281b51e1509adc177218dd482e4e8a4cc','0xd9994fea36a57fcb52d4c31c2325e394a79cef8af42e10514277d3961fc5593b'),
 (26301955,'0x30d303960b625f97d8b479afe4e4e880b3fbb045','0xe90608f24b153e894ec64a7d938710d2a84306053f4bb2c5c281956867276003'),
 (26301942,'0xd4df826ec0235b1e9862da59287033d37d9b46bf','0x0f4382e7a1c14c9cfeca635ed7de77c70dbd34fab8000781a2f935a71c1f5e9e'),
]
for b,u,tx in cands:
    try:
        rx=rpc('eth_getTransactionReceipt',[tx])
        gas=int(rx['gasUsed'],16); fee=int(rx['effectiveGasPrice'],16)
    except Exception as e:
        gas=fee=None; print('receipt fail',e)
    hfs={}
    for off in (1,100,500,1500):
        try: hfs[off]=hf(u,b-off)
        except Exception as e: hfs[off]=f'ERR {e}'
    blk=rpc('eth_getBlockByNumber',[hex(b-1),False])
    base=int(blk['baseFeePerGas'],16) if blk.get('baseFeePerGas') else None
    ts=int(blk['timestamp'],16)
    print(json.dumps(dict(block=b,user=u[:10],hf_by_parent_offset=hfs,winner_gas=gas,winner_effFeeWei=fee,era_baseFee=base,parent_ts=ts)))
