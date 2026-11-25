import json,urllib.request,os
URL=os.environ['RPC_RELAY_URL']+'/base?lane=research'
def req(m,p):
    body=json.dumps({"jsonrpc":"2.0","id":1,"method":m,"params":p}).encode()
    rq=urllib.request.Request(URL,data=body,headers={"content-type":"application/json"})
    d=json.loads(urllib.request.urlopen(rq,timeout=60).read())
    if 'error' in d: raise SystemExit('relay error: '+json.dumps(d['error'])[:200])
    return d['result']
def call(to,data):
    r=req('eth_call',[{"to":to,"data":data},"latest"])
    return r
def word(f,addr=None,fee=None):
    w=f[2:].rjust(64,'0')
    if addr: w+=addr[2:].rjust(64,'0')
    if fee is not None: w+=hex(fee)[2:].rjust(64,'0')
    return '0x'+w
def hexi(h): return int(h,16) if isinstance(h,str) else None
M={'mAERO':'0x73902f619ceb9b31fd8efecf435cbdf89e369ba6','mWELL':'0xdc7810b47eaab250de623f0ee07764afa5f71ed1'}
TOK={'AERO':'0x940181a94a35a4569e4529a3cdfb74e38fd98631','WELL':'0xa88594d404727625a9437c3f886c7643872296ae','WETH':'0x4200000000000000000000000000000000000006','USDC':'0x833589fcd6edb6e08f4c7c32d4f71b54bda02913'}
PANF='0x9cb220581b91b0c83223012fe69688b92ad07a76'
out={}
for name,mk in M.items():
    for sel,sig in [('0x182df0f5','exchangeRateStored()'),('0x668aa824','oraclePrice()'),('0x3b1d21a2','cash()'),('0x18160ddd','totalSupply()')]:
        try: out[name+'.'+sig]=call(mk,sel)
        except SystemExit as e: out[name+'.'+sig]=str(e)
GP='0x1698ee82'
pools={}
for a,b in [('WELL','WETH'),('WELL','USDC'),('AERO','WETH'),('AERO','USDC')]:
    for fee in [100,500,2500,10000]:
        r=call(PANF,GP+TOK[a]+TOK[b]+hex(fee)[2:].rjust(64,'0') if False else '0x'+GP[2:]+TOK[a][2:].rjust(64,'0')+TOK[b][2:].rjust(64,'0')+hex(fee)[2:].rjust(64,'0'))
        p=r if isinstance(r,str) else None
        if p and p!='0x' and set(p[2:].strip('0')[-40:] or 'x')!=set('0'):
            pools[f'{a}-{b}-{fee}']=p
            break
print(json.dumps(pools,indent=1))
TB='0x523fba7f'
for k,p in pools.items():
    r=call(p,'0x'+TB[2:]+p[2:].rjust(64,'0'))
    print(k,'tokenBalances:',r)
print(json.dumps({k:v if isinstance(v,str) else v for k,v in out.items()},indent=1))
