import json, urllib.request, subprocess, sys
MORPHO='0xbbbbbbbbbb9cc5e90e3b3af64bdaf62c37eeffcb'
FORK='http://127.0.0.1:9001'
HP='0x52a528df'
READS={'0x70a08231','0xa9059cbb','0x23b872dd','0xdd62ed3e','0x5c60da1b','0xfeaf968c','0xf69058c1','0x095ea7b3'}
CAPS=json.load(open('/srv/farm/ws/scratch/mb-caps2.json'))
LADDER=[1,2,8,32,128]
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
    r=subprocess.run(['fork','trace','base',tx],capture_output=True,text=True).stdout
    d=json.loads(r[r.find('{'):])
    res=find(d['calls'],d['to'])
    if not res: out.append({'block':C,'error':'no morpho call'}); continue
    frm,data=res
    n=(len(data)-10)//64
    w=[data[10+i*64:10+(i+1)*64] for i in range(n)]
    seized=cap.get('seized') or 0
    patched=False
    for i,x in enumerate(w):
        v=int(x,16)
        if v==seized and v>0:
            w[i]=format(v-1,'x').rjust(64,'0'); patched=True; break
    row={'block':C,'repaid':cap['repaid'],'patched':patched,'wrapper':frm,'probes':{}}
    data='0x'+''.join(w)
    for k in LADDER:
        subprocess.run(['fork','reset','base',str(C-k)],capture_output=True,text=True)
        j=rpc('eth_call',[{'from':frm,'to':MORPHO,'data':data,'gas':'0x7a120'},'latest'])
        if 'result' in j: v='LIQ'
        else:
            e=j['error']; de=e.get('data','') or ''
            sel=de[:10] if isinstance(de,str) else ''
            msg=e.get('message','')
            v='HP' if sel==HP else ('X'+sel if sel else 'R')
        row['probes'][k]=v
        if v=='HP': break
    out.append(row); print(json.dumps(row),flush=True)
json.dump(out,open('/srv/farm/ws/scratch/mb-windows5.json','w'),indent=1)
