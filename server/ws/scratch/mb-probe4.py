import json, urllib.request, subprocess, sys, time
MORPHO='0xbbbbbbbbbb9cc5e90e3b3af64bdaf62c37eeffcb'
FORK='http://127.0.0.1:9001'
HP='0x52a528df'; DP='0x1314fcef'
READS={'0x70a08231','0xa9059cbb','0x23b872dd','0xdd62ed3e','0x5c60da1b','0xfeaf968c','0xf69058c1','0x095ea7b3'}
# capture: block, tx, repaidShares hex from ledger events
CAPS=[l for l in json.load(open('/srv/farm/ws/scratch/mb-caps-full.json'))]
LADDER=[1,2,8,32,128,512,1024,4096]
def rpc(m,p):
    body=json.dumps({"jsonrpc":"2.0","id":1,"method":m,"params":p}).encode()
    req=urllib.request.Request(FORK,body,{'content-type':'application/json'})
    return json.loads(urllib.request.urlopen(req,timeout=40).read())
def find(c,p):
    for x in c:
        if x.get('to','').lower()==MORPHO and x.get('input','')[:10] not in READS and len(x.get('input',''))>=74: return p,x['input']
        r=find(x.get('calls',[]),x.get('to',p))
        if r: return r
out=[]
for cap in CAPS:
    C=cap['block']; tx=cap['tx']
    r=subprocess.run(['fork','trace','base',tx],capture_output=True,text=True)
    txt=r.stdout; d=json.loads(txt[txt.find('{'):])
    gasused=int(d['gasUsed'],16)
    res=find(d['calls'],d['to'])
    if not res: out.append({'block':C,'error':'no morpho call'}); continue
    frm,data=res
    n=(len(data)-10)//64
    w=[data[10+i*64:10+(i+1)*64] for i in range(n)]
    want=format(int(cap['repaidShares']),'x').rjust(64,'0')
    patched=None
    for i,x in enumerate(w):
        if x==want:
            w2=list(w); w2[i]='000000000000000000000000000000000000000000000000ffffffffffffffffffffffff'
            patched='0x'+''.join(w2)
    row={'block':C,'repaid':cap['repaid'],'gasUsed':gasused,'wrapper':frm,'patched':patched is not None,'probes':{}}
    data=patched or data
    for k in LADDER:
        subprocess.run(['fork','reset','base',str(C-k)],capture_output=True,text=True)
        j=rpc('eth_call',[{'from':frm,'to':MORPHO,'data':data,'gas':'0x7a120'},'latest'])
        if 'result' in j: v='LIQ'
        else:
            e=j['error']; de=e.get('data','') if isinstance(e,dict) else ''
            sel=de[:10] if isinstance(de,str) and len(de)>=10 else ''
            msg=e.get('message','') if isinstance(e,dict) else str(e)
            v='HP' if sel==HP else ('DP' if sel==DP else ('X'+sel if sel else 'REVERT:'+msg[:32]))
        row['probes'][k]=v
        if v=='HP': break
    out.append(row); print(json.dumps(row),flush=True)
json.dump(out,open('/srv/farm/ws/scratch/mb-windows3.json','w'),indent=1)
