import json, urllib.request, os
REL=os.environ['RPC_RELAY_URL']
def call(m,p,lane='research'):
    b=json.dumps({"jsonrpc":"2.0","id":1,"method":m,"params":p}).encode()
    req=urllib.request.Request(f"{REL}/ethereum?lane={lane}",data=b,headers={'content-type':'application/json'})
    return json.loads(urllib.request.urlopen(req,timeout=30).read())
TRANSFER="0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
MORPHO="0xbbbbbbbbbb9cc5e90e3b3af64bdaf62c37eeffcb"
def pad(a): return "000000000000000000000000"+a[2:]
def val(lg): 
    d=lg['data'][2:]
    return int(d[:64],16) if len(d)>=64 else int(d,16)
events=[json.loads(l) for l in open('scratch/whale_events.json')]
best={}
for e in events:
    m=e['market']
    if m not in best or float(e['repaid'])>float(best[m]['repaid']): best[m]=e
out=[]
dbg=True
for m,e in sorted(best.items()):
    blk=hex(int(e['block']))
    loan=coll=None
    r=call('eth_getLogs',[{"address":None,"fromBlock":blk,"toBlock":blk,"topics":[TRANSFER,None,pad(MORPHO)]}]).get('result') or []
    if dbg: print('DBG logs-to-morpho in blk', len(r), 'sample tx', r[0]['transactionHash'] if r else None, flush=True); dbg=False
    for lg in r:
        if lg['transactionHash']==e['tx_hash']:
            v=val(lg)
            if abs(v-float(e['repaid']))/max(v,1)<1e-6: loan=lg['address']; break
    bor=e.get('borrower')
    rep=int(float(e['repaid']))
    seized=int(float(e['seized'])) if e.get('seized') else 0
    if bor and seized>0:
        r2=call('eth_getLogs',[{"address":None,"fromBlock":blk,"toBlock":blk,"topics":[TRANSFER,pad(bor),None]}]).get('result') or []
        for lg in r2:
            if lg['transactionHash']==e['tx_hash'] and lg['address']!=loan:
                v=val(lg)
                if abs(v-seized)/max(seized,1)<1e-6: coll=lg['address']; break
    print(m[:12], 'loan=',loan, 'coll=',coll, 'repaid=',e['repaid'], flush=True)
    out.append({'market':m,'loan':loan,'coll':coll,'repaid':e['repaid'],'seized':e.get('seized'),'block':e['block'],'tx':e['tx_hash'],'borrower':bor})
json.dump(out,open('scratch/whale_named.json','w'),indent=1)
