import json, urllib.request, os
RELAY=os.environ.get('RPC_RELAY_URL','http://127.0.0.1:8545')
EP=f"{RELAY}/base?lane=research"
mid=0
def rpc(method, params):
    global mid
    body=json.dumps({"jsonrpc":"2.0","id":mid,"method":method,"params":params}).encode()
    req=urllib.request.Request(EP, data=body, headers={"content-type":"application/json"})
    j=json.loads(urllib.request.urlopen(req, timeout=60).read())
    if 'error' in j: return {'error': j['error']}
    return j['result']
def call(to, data, blk='latest'):
    return rpc('eth_call', [{'to':to,'data':data}, blk])
def words(r): return [r[2+64*i:2+64*(i+1)] for i in range(0,(len(r)-2)//64)] if isinstance(r,str) else None
def h(b): return hex(b)
M_EURC='0xedc817a28e8b93b03976fbd4a3ddbc9f7d176c22'   # mEURC mToken (collateral seized)
M_EURC_BORROW='0xb682c840b5f4fc58b20769e691a6fa1305a501a2' # mToken EURC borrow market
BOR='0x33a7ec1055edd4cc35ef289156c7a7a078043474'
COMP='0xfbb21d0380bee3312b33c4353c8936a0f13ef26c'
MORPHO='0xbbbbbbbbbb9cc5e90e3b3af64bdaf62c37eeffcb'
SEL_UNDER='0x7158da7c'; SEL_DEC='0x313ce567'; SEL_POOL='0x156522a8'; SEL_CASH='0x3b1d21a2'; SEL_LIQ='0x5ec88c79'; SEL_BOF='0x70a08231'
out={}
# identity
u=call(M_EURC, SEL_UNDER)
eurc = '0x'+u[-40:] if isinstance(u,str) else {'error':u}
out['eurc_from_mEURC']=eurc
u2=call(M_EURC_BORROW, SEL_UNDER)
out['eurc_from_borrow_mkt']='0x'+u2[-40:] if isinstance(u2,str) else {'error':u2}
d=call(eurc if isinstance(eurc,str) else M_EURC, SEL_DEC)
out['eurc_decimals']=int(d,16) if isinstance(d,str) else d
# Morpho pool for EURC
p=call(MORPHO, SEL_POOL + eurc[-40:].rjust(64,'0') if isinstance(eurc,str) else SEL_POOL)
out['morpho_pool_EURC']=p
if isinstance(p,str) and int(p,16)!=0:
    pool='0x'+p[-40:]
    bal=call(eurc, SEL_BOF + pool[2:].rjust(64,'0'))
    out['eurc_balance_pool']=int(bal) if isinstance(bal,str) else bal
# per-capture measurements
for cap in (55046981, 55076179, 55095244):
    b1=h(cap-1)
    cash=call(M_EURC, SEL_CASH, b1)
    out[f'getCash_mEURC@{cap-1}']=int(cash,16) if isinstance(cash,str) else cash
    bofb=call(M_EURC, SEL_BOF + BOR[2:].rjust(64,'0'), b1)
    out[f'mEURCbal_borrower@{cap-1}']=int(bofb,16) if isinstance(bofb,str) else bofb
    if isinstance(eurc,str):
        be=call(eurc, SEL_BOF + BOR[2:].rjust(64,'0'), b1)
        out[f'EURCbal_borrower@{cap-1}']=int(be,16) if isinstance(be,str) else be
    for lag in (1, 51, 501, 1501, 5001):
        bb=h(cap-lag)
        r=call(COMP, SEL_LIQ + BOR[2:].rjust(64,'0'), bb)
        if isinstance(r,str):
            w=[int(x,16) for x in words(r)]
            out[f'sf_{cap}-{lag}']=f"liq={w[0]} short={w[1]}"
        else: out[f'sf_{cap}-{lag}']=r
print(json.dumps(out, indent=1))
