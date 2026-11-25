import json, subprocess, urllib.request, os
FORK='http://127.0.0.1:9001'
RELAY=os.environ['RPC_RELAY_URL']
LANE='research'
CH='base'
def fork(m,p):
    body=json.dumps({"jsonrpc":"2.0","id":1,"method":m,"params":p}).encode()
    req=urllib.request.Request(FORK,body,{'content-type':'application/json'})
    return json.loads(urllib.request.urlopen(req,timeout=60).read())
def relay(m,p):
    body=json.dumps({"jsonrpc":"2.0","id":1,"method":m,"params":p}).encode()
    req=urllib.request.Request(f"{RELAY}/{CH}?lane={LANE}",body,{'content-type':'application/json'})
    return json.loads(urllib.request.urlopen(req,timeout=60).read())['result']

SEL=json.load(open('/srv/farm/ws/scratch/mb157-sel.json'))
extra={55675686,55691524}
rows=[json.loads(l) for l in open('/srv/farm/ws/scratch/mb157-caps.json') if l.strip()]
rows=[r for r in rows if '_note' not in r]
for r in rows:
    if r['block'] in extra and all(s['block']!=r['block'] for s in SEL): SEL.append(r)
def walk_find(c,best,depth=0):
    if c.get('input','')[2:10]=='feaf968c' and depth>=best[0]: best[:]=[depth,c['to'],c.get('output','')]
    for ch in c.get('calls',[]): walk_find(ch,best,depth+1)
def word0(o): return int(o[2:66],16) if len(o)>=66 else None
import glob, os
tr={}
for C,tx in [(r['block'],r['tx_hash']) for r in SEL]:
    f=f'/srv/farm/ws/scratch/mb157-tr-{C}.json'
    if os.path.exists(f): d=json.load(open(f))
    else:
        p=subprocess.run(['fork','trace','base',tx],capture_output=True,text=True).stdout
        d=json.loads(p[p.find('{'):]); json.dump(d,open(f,'w'))
    best=[-1,None,'']; walk_find(d,best)
    tr[C]=best[1:]
    print(C,'feed',tr[C][0][:12],hex(word0(tr[C][1])),flush=True)
groups={}
for C,(feed,output) in tr.items():
    if not feed: groups.setdefault('none',[]).append(C); continue
    groups.setdefault((feed,word0(output)),[]).append(C)
pub={}
LOOK=4096
for key,Cs in groups.items():
    if key=='none': continue
    feed,R=key
    Cmin=min(Cs); lo,hi=Cmin-LOOK,Cmin-1; probes=0
    while lo<hi:
        mid=(lo+hi+1)//2
        fork('eth_call',[{'from':'0x000000000000000000000000000000000000f00d','to':feed,'data':'0xfeaf968c'},f'0x{mid:x}'])
        probes+=1
        j=fork('eth_call',[{'from':'0x000000000000000000000000000000000000f00d','to':feed,'data':'0xfeaf968c'},f'0x{mid:x}'])
        ok='result' in j and word0(j['result'])==R
        if ok: hi=mid
        else: lo=mid+1
        if probes>16: break
    j=fork('eth_call',[{'from':'0x000000000000000000000000000000000000f00d','to':feed,'data':'0xfeaf968c'},f'0x{lo:x}'])
    Pb=lo if ('result' in j and word0(j['result'])==R) else None
    pub[key]={'Pb':Pb,'probes':probes}
    print('pub',feed[:12],hex(R),'Pb',Pb,flush=True)
# relay headers once: range covers all Pb..C
lo=min(v['Pb'] for v in pub.values() if v['Pb']) if any(v['Pb'] for v in pub.values()) else min(r['block'] for r in SEL)-LOOK
hi=max(r['block'] for r in SEL)
hdrs={}
def hdr(b):
    if b not in hdrs: hdrs[b]=relay('eth_getBlockByNumber',[f'0x{b:x}',False])
    return hdrs[b]
for key in pub:
    if pub[key]['Pb']: hdr(pub[key]['Pb'])
for C in sorted(tr): hdr(C)
ETH_USD=2050.0
final=[]
for r in SEL:
    C=r['block']
    feed,output=tr[C]
    row={'block':C,'tx':r['tx_hash'],'repaid_usd':round(int(r['ra'])/1e6,2)}
    key=(feed,word0(output)) if feed else None
    g=pub.get(key)
    if key and g and g['Pb']:
        Pb=g['Pb']; k=C-Pb
        tC=int(hdr(C)['timestamp'],16); tP=int(hdr(Pb)['timestamp'],16)
        baseFee=int(hdr(C)['baseFeePerGas'],16)
        gasUsed=int(json.load(open(f'/srv/farm/ws/scratch/mb157-tr-{C}.json')).get('gasUsed','0'),16)
        bonus=0.04384*row['repaid_usd']; gusd=gasUsed*baseFee/1e18*ETH_USD
        row.update({'feed':feed[:12],'Pb':Pb,'window_blocks':k,'window_seconds':tC-tP,'race':k<=2,
                    'bonus_usd':round(bonus,2),'gas_usd':round(gusd,2),'net_usd':round(bonus-gusd,2)})
    else:
        row['note']='no latestRoundData (static oracle)' if not feed else 'Pb probe failed'
    final.append(row); print(json.dumps(row),flush=True)
json.dump(final,open('/srv/farm/ws/scratch/mb158-window.json','w'),indent=1)
json.dump({'groups':{str(k):v for k,v in groups.items()},'pub':{str(k):v for k,v in pub.items()}},open('/srv/farm/ws/scratch/mb158-pub.json','w'),indent=1)
