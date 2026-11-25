import json,urllib.request,os
URL=os.environ['RPC_RELAY_URL']+'/base?lane=research'
def req(m,p):
    body=json.dumps({"jsonrpc":"2.0","id":1,"method":m,"params":p}).encode()
    rq=urllib.request.Request(URL,data=body,headers={"content-type":"application/json"})
    d=json.loads(urllib.request.urlopen(rq,timeout=90).read())
    if 'error' in d: print('ERR',m,json.dumps(d['error'])[:140]); return None
    return d['result']
def call(to,data): return req('eth_call',[{"to":to,"data":data},"latest"])
def pad(a): return a[2:].lower().rjust(64,'0')
def sel(hexsel,addr=None,fee=None):
    w=hexsel[2:]
    if addr: w+=pad(addr)
    if fee is not None: w+=hex(fee)[2:].rjust(64,'0')
    return '0x'+w
TOK={'AERO':'0x940181a94a35a4569e4529a3cdfb74e38fd98631','WELL':'0xa88594d404727625a9437c3f886c7643872296ae','WETH':'0x4200000000000000000000000000000000000006','USDC':'0x833589fcd6edb6e08f4c7c32d4f71b54bda02913'}
MKT={'AERO':'0x73902f619ceb9b31fd8efecf435cbdf89e369ba6','WELL':'0xdc7810b47eaab250de623f0ee07764afa5f71ed1'}
FEEDER='0xec942be8a8114bfd0396a5052c36027f2ca6a9d0'
res={}
for k in ['AERO','WELL']:
    res[k+'.balanceOfUnderlyingOfMarket']=call(TOK[k],sel('0x70a08231',MKT[k]))  # underlying balance of mToken
    res[k+'.getUnderlyingPrice']=call(FEEDER,sel('0xfc57d4df',MKT[k]))
print(json.dumps(res,indent=1))
# traces
for name,h in [('AERO-55297682','0xf0579b9d69c3712b5ddbdc91b033e98bf4ff3714702232d003d772258bbc2f55'),('WELL-55297688','0x6c8da0a6c3bd0350ac0da1c061bc9583b6f3ae5d18a24686c005ecbc8c65811d')]:
    t=req('debug_traceTransaction',[h,{"tracer":"callTracer"}])
    if not t: continue
    def walk(fr,out):
        out.append(fr)
        for c in fr.get('calls',[]) or []: walk(c,out)
        return out
    frs=walk(t,[])
    addrs=sorted({f.get('from') for f in frs if f.get('from')} | {f.get('to') for f in frs if f.get('to')})
    interesting=[a for a in addrs if a not in (TOK['AERO'],TOK['WELL'],TOK['WETH'],TOK['USDC']) and a not in list(MKT.values()) and FEEDER not in a]
    print('---',name,'frames',len(frs))
    # print swap-ish calls: token transfers involving non-token contracts
    for f in frs:
        i=f.get('input') or ''
        if f.get('to') in [TOK['AERO'],TOK['WELL'],TOK['USDC']] and i[2:10]==(sel('0xa9059cbb')[2:]):
            pass
    print('contracts:',json.dumps(interesting))
    json.dump(t,open(f'/srv/farm/ws/scratch/mw-trace-{name}-191de.json','w'))
