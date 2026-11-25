import json, subprocess, urllib.request, os
FORK='http://127.0.0.1:9001'
RELAY=os.environ['RPC_RELAY_URL']
def fork(m,p):
    body=json.dumps({"jsonrpc":"2.0","id":1,"method":m,"params":p}).encode()
    req=urllib.request.Request(FORK,body,{'content-type':'application/json'})
    return json.loads(urllib.request.urlopen(req,timeout=60).read())
def relay(m,p):
    body=json.dumps({"jsonrpc":"2.0","id":1,"method":m,"params":p}).encode()
    req=urllib.request.Request(f"{RELAY}/base?lane=research",body,{'content-type':'application/json'})
    return json.loads(urllib.request.urlopen(req,timeout=60).read())['result']
def word0(o): return int(o[2:66],16) if len(o)>=66 else None
def walk_find(c,best,depth=0):
    if c.get('input','')[2:10]=='feaf968c' and depth>=best[0]: best[:]=[depth,c['to'],c.get('output','')]
    for ch in c.get('calls',[]): walk_find(ch,best,depth+1)

SEL=json.load(open('/srv/farm/ws/scratch/mb157-sel.json'))
extra={55675686,55691524}
rows=[json.loads(l) for l in open('/srv/farm/ws/scratch/mb157-caps.json') if l.strip()]
rows=[r for r in rows if '_note' not in r]
for r in rows:
    if r['block'] in extra and all(s['block']!=r['block'] for s in SEL): SEL.append(r)

tr={}
for r in SEL:
    C,tx=r['block'],r['tx_hash']
    f=f'/srv/farm/ws/scratch/mb157-tr-{C}.json'
    if os.path.exists(f): d=json.load(open(f))
    else:
        s=subprocess.run(['fork','trace','base',tx],capture_output=True,text=True).stdout
        d=json.loads(s[s.find('{'):]); json.dump(d,open(f,'w'))
    best=[-1,None,'']
    walk_find(d,best)
    tr[C]=(best[1], best[2], int(d.get('gasUsed','0'),16))
    print('traced',C,tr[C][0] and tr[C][0][:12],hex(word0(tr[C][1])) if tr[C][1] else '',flush=True)

groups={}
for C,(feed,output,g) in tr.items():
    if not feed: continue
    groups.setdefault((feed,word0(output)),[]).append(C)

# tagged probes: reset the fork to Cmin-1 once per group, then probe tags <= that
pub={}
LOOK=8192
PROBE={'from':'0x000000000000000000000000000000000000f00d','to':None,'data':'0xfeaf968c'}
for key,Cs in groups.items():
    feed,R=key
    Cmin=min(Cs)
    fork('anvil_reset',[{'jsonRpcUrl':None,'historique':None,'forkBlockNumber':f'0x{Cmin-1:x}'}]) if False else subprocess.run(['fork','reset','base',str(Cmin-1)],capture_output=True,text=True)
    def probe(tag):
        return fork('eth_call',[{'from':'0x000000000000000000000000000000000000f00d','to':feed,'data':'0xfeaf968c'},f'0x{tag:x}'])
    hi=Cmin-1; j=probe(hi); lo=Cmin-LOOK
    if not('result' in j and word0(j['result'])==R):
        pub[key]={'Pb':None,'why':'not visible at C-1: '+json.dumps(j.get('error',{}).get('message',''))[:80]}
        print('group',feed[:12],hex(R),'C-1 probe failed',pub[key]['why'],flush=True); continue
    probes=0; Pb=None
    while lo<hi:
        mid=(lo+hi+1)//2
        j=probe(mid); probes+=1
        ok='result' in j and word0(j['result'])==R
        if ok: hi=mid
        else: lo=mid+1
        if probes>14: break
    j=probe(lo)
    if 'result' in j and word0(j['result'])==R: Pb=lo
    pub[key]={'Pb':Pb,'probes':probes,'err_lo':None if Pb else json.dumps(j.get('error',{}).get('message',''))[:100]}
    print('pub',feed[:12],hex(R),'Pb',Pb,'probes',probes,flush=True)

hdrs={}
def hdr(b):
    if b not in hdrs: hdrs[b]=relay('eth_getBlockByNumber',[f'0x{b:x}',False])
    return hdrs[b]
ETH_USD=2050.0
final=[]
for r in SEL:
    C=r['block']; feed,output,g=tr[C]
    row={'block':C,'tx':r['tx_hash'],'repaid_usd':round(int(r['ra'])/1e6,2)}
    key=(feed,word0(output)) if feed else None
    Pc=hdr(C)
    row['gas_usd']=round(g*int(Pc['baseFeePerGas'],16)/1e18*ETH_USD,3)
    row['bonus_usd']=round(0.04384*row['repaid_usd'],2)
    row['net_usd']=round(row['bonus_usd']-row['gas_usd'],2)
    g2=pub.get(key) if key else None
    if key and g2 and g2['Pb']:
        Pb=g2['Pb']; k=C-Pb
        tC=int(Pc['timestamp'],16); tP=int(hdr(Pb)['timestamp'],16)
        row.update({'feed':feed[:10],'round':hex(word0(output)),'Pb':Pb,'window_blocks':k,'window_seconds':tC-tP,'race':k<=2})
    else:
        row['note']= 'no latestRoundData in tx' if not feed else (g2 or {}).get('why','probe failed')
    final.append(row); print(json.dumps(row),flush=True)
json.dump(final,open('/srv/farm/ws/scratch/mb159-window.json','w'),indent=1)
