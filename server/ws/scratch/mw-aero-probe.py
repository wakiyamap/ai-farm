import json,urllib.request,os
URL=os.environ['RPC_RELAY_URL']+'/base?lane=research'
def call(to,data,blk):
    rq=urllib.request.Request(URL,data=json.dumps({"jsonrpc":"2.0","id":1,"method":"eth_call","params":[{"to":to,"data":data},"%s"%blk]}).encode(),headers={"content-type":"application/json"})
    r=json.loads(urllib.request.urlopen(rq,timeout=60).read())
    if 'error' in r: return ('ERR',r['error'])
    return r['result']
def h64(a): return a[2:].rjust(64,'0') if a.startswith('0x') else a.rjust(64,'0')
def addr(a): return h64(a)
COMP='0xfbb21d0380bee3312b33c4353c8936a0f13ef26c'
MUSDC='0xedc817a28e8b93b03976fbd4a3ddbc9f7d176c22'
LIQ='0x5ec88c79'; BBC='0x17bfdfbc'
holders={'c8f8c2dd':('0xc8f8c2dde5dabaa585acdbc7fec3db639e97f3eb',55297681),
         '1a73d5b9_a':('0x1a73d5b9fe5b1937db4ebd03ba3937211786fb57',55363031),
         '1a73d5b9_b':('0x1a73d5b9fe5b1937db4ebd03ba3937211786fb57',55450919)}
out={}
for k,(h,b) in holders.items():
    blk=hex(b)
    r=call(COMP,LIQ+h64(h[2:]),blk)
    words=[r[i*64:(i+1)*64] for i in range(0,len(r[2:])//64)] if isinstance(r,str) and len(r)>10 else r
    liq=int(words[0],16)/1e18 if isinstance(words,list) and len(words)>=3 else None
    sf=int(words[1],16)/1e18 if isinstance(words,list) and len(words)>=3 else None
    r2=call(MUSDC,BBC+h64(h[2:]),blk)
    out[k]={'blk':b,'liquidity':liq,'shortfall':sf,'borrowCur':r2 if isinstance(r2,str) else str(r2)}
    print(k,b,'liquidity',liq,'shortfall',sf,'borrowCurrent raw',r2)
AERO='0x940181a94f1542a717986196649290292a544f6b'
WETH='0x4200000000000000000000000000000000000006'
POOL_AERO='0xdfe5f275020def30993f042174fc2d335678b626'
POOL_WETH_USDC='0x4a7af46bc8abc00048c6c7920a1488daf568366c'
TOK='0x9d63848a'; RES='0x0902f1ac'
r=call(POOL_AERO,TOK,'latest')
print('AERO pool tokens()', r)
r=call(POOL_AERO,RES,'latest')
print('AERO pool getReserves()', r)
r=call(POOL_WETH_USDC,RES,'latest')
print('WETHUSDC pool getReserves()', r)
bal=call(WETH,'0x70a08231'+h64(POOL_WETH_USDC[2:]),'latest')
print('WETH bal of 0x4a7af46b pool', bal)
json.dump(out,open('scratch/mw-aero-probe.json','w'),indent=1)
