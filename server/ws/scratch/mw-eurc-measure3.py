import json, urllib.request, os
RELAY=os.environ.get('RPC_RELAY_URL','http://127.0.0.1:8545')
EP=f"{RELAY}/base?lane=research"
def rpc(method, params):
    body=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    req=urllib.request.Request(EP, data=body, headers={"content-type":"application/json"})
    j=json.loads(urllib.request.urlopen(req, timeout=60).read())
    return j.get('result', j.get('error'))
def call(to, data, blk='latest'):
    return rpc('eth_call', [{'to':to,'data':data}, blk])
EURC='0x60a3e35Cc302BFA44cB288bc5A4f316FDb1aDb42'
MORPHO='0xbbbbbbbbbb9cc5e90e3b3af64bdaf62c37eeffcb'
M_WETH='0x628ff693426583d9a7fb391e54366292f509d457'
BOR1='0x1e61f524d60e77e58119a24fadd3ff8b0732caa6'
COMP='0xfbb21d0380bee3312b33c4353c8936a0f13ef26c'
addr=lambda a: a[2:].lower().rjust(64,'0')
out={}
for name,sel in (('pool',0x156522a8),('poolFor',0xb700a49e),('pools',0xa4063dbc)):
    r=call(MORPHO, hex(sel)[2:].rjust(8,'0')+addr(EURC))
    out['morpho_'+name]= ('0x'+r[-40:] if (isinstance(r,str) and len(r)>=42) else r)
# whale borrower 0x1e61f5 window at 54697042
for lag in (1,51,501,1501,5001):
    r=call(COMP, '0x5ec88c79'+addr(BOR1), hex(54697042-lag))
    if isinstance(r,str):
        w=[int(r[2+64*i:2+64*(i+1)],16) for i in range(3)]
        out[f'whale_sf_54697042-{lag}']=(w[0],w[1],w[2])
    else: out[f'whale_sf_54697042-{lag}']=r
r=call(M_WETH,'0x3b1d21a2', hex(54697041))
out['cash_mWETH@54697041']=int(r,16) if isinstance(r,str) else r
print(json.dumps(out,indent=1))
