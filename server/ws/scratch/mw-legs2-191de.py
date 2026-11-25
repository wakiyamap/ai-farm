import json,urllib.request,os
URL=os.environ['RPC_RELAY_URL']+'/base?lane=research'
def req(m,p):
    body=json.dumps({"jsonrpc":"2.0","id":1,"method":m,"params":p}).encode()
    rq=urllib.request.Request(URL,data=body,headers={"content-type":"application/json"})
    d=json.loads(urllib.request.urlopen(rq,timeout=60).read())
    if 'error' in d:
        print('ERR',json.dumps(d['error'])[:160]); return None
    return d['result']
def call(to,data): return req('eth_call',[{"to":to,"data":data},"latest"])
def addr40(w):
    w=w[2:] if isinstance(w,str) else ''
    return '0x'+w[-40:] if len(w)>=40 else None
M={'mAERO':'0x73902f619ceb9b31fd8efecf435cbdf89e369ba6','mWELL':'0xdc7810b47eaab250de623f0ee07764afa5f71ed1'}
TOK={'AERO':'0x940181a94a35a4569e4529a3cdfb74e38fd98631','WELL':'0xa88594d404727625a9437c3f886c7643872296ae','WETH':'0x4200000000000000000000000000000000000006','USDC':'0x833589fcd6edb6e08f4c7c32d4f71b54bda02913'}
PANF='0x9cb220581b91b0c83223012fe69688b92ad07a76'
UNIF='0x3317ad555803e870Aba8a68Eed4E4D459970d40c'
GP='0x1698ee82'
def pad(a): return a[2:].lower().rjust(64,'0')
out={}
for name,mk in M.items():
    for sel,sig in [('0x182df0f5','exchangeRateStored()'),('0x668aa824','oraclePrice()'),('0x3b1d21a2','cash()'),('0x18160ddd','totalSupply()')]:
        out[name+'.'+sig]=call(mk,sel)
pools={}
for fac,fees,tag in [(PANF,[100,500,2500,10000],'pancake'),(UNIF,[500,2500,10000,30000,100000],'uni')]:
    for a,b in [('WELL','WETH'),('WELL','USDC'),('AERO','WETH'),('AERO','USDC')]:
        key=f'{tag}-{a}-{b}'
        for fee in fees:
            r=call(fac,'0x'+GP[2:]+pad(TOK[a])+pad(TOK[b])+hex(fee)[2:].rjust(64,'0'))
            p=addr40(r) if r else None
            if p and p!='0x0000000000000000000000000000000000000000':
                pools[key+'-'+str(fee)]=p
                break
print('POOLS:'); print(json.dumps(pools,indent=1))
BO='0x70a08231'
for k,p in pools.items():
    for tkn in [TOK[k.split('-')[1]],TOK[k.split('-')[2]]]:
        r=call(tkn,'0x'+BO[2:]+pad(p))
        print(k,'balanceOf',tkn[:8],r)
print('MTOKEN READS:'); print(json.dumps(out,indent=1))
