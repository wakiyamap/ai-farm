import json, urllib.request, subprocess, sys, time
MORPHO='0xbbbbbbbbbb9cc5e90e3b3af64bdaf62c37eeffcb'
FORK='http://127.0.0.1:9001'
HP='0x52a528df'   # HEALTHY_POSITION()
DP='0x1314fcef'   # DEBT_PRECISION()
READS={'0x70a08231','0xa9059cbb','0x23b872dd','0xdd62ed3e','0x5c60da1b','0xfeaf968c','0xf69058c1','0x6eb71926','0x67c572ea','0x0709a8d6','0x313ce567','0x06fdde03','0x95d8c86e6','0x1816f495','0x095ea7b3','0x8b5c8df5','0xdde5345c'}
CAPS=[
 (56265482,'0x4dc2631721bb8a491e7e43524c171d6f84346f7657a18a09de088b107ad2a0f8','whale 157133 USDC repaid, baddebt 157133'),
 (56160131,'0x097700d317198cd643ae9c0b292a5f0b100ffb023f2fc2ec7ee3d2a3a8465990','mega 9.74M repaid'),
 (56160094,'0x3ce651419c3814376194aad7297bd79ade07bf053b07d696f413f2b61d47bdd6','1.387M repaid'),
 (56160057,'0xd49d07fcdb55494b23d5e35881ff016484e95dbf84811ed525fc411c09172a10','10470 repaid'),
 (55951354,'0x13bf67e4131714f36bc24283bd1d8ef95d1471303661d022d32de2b62f74cf4e','47732 repaid'),
 (56245267,'0x8840c48bd2f5905d655f27f1af822d12d0d75959b56efb6f6a5c52efb0eba02f','127 repaid'),
 (56374332,'0xf1c68254b2fa683151032b2bb8c3ebbd74746057baa224dc5be8aee088dbc81c','29.6 repaid'),
]
LADDER=[1,2,4,8,16,32,64,128,256,512,1024,2048,4096]
def rpc(method,params):
    body=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    req=urllib.request.Request(FORK,body,{'content-type':'application/json'})
    return json.loads(urllib.request.urlopen(req,timeout=30).read())
def find_morpho(calls, parent_to):
    for c in calls:
        inp=c.get('input','')
        if c.get('to','').lower()==MORPHO and inp[:10] not in READS and len(inp)>42:
            return parent_to, inp, c.get('error')
        r=find_morpho(c.get('calls',[]), c.get('to',parent_to))
        if r: return r
    return None
def patch(data):
    w=[data[10+i*64:10+(i+1)*64] for i in range((len(data)-10)//64)]
    bi=next(i for i,x in enumerate(w) if int(x,16)>0 and x[24:].strip('0')=='' and int(x[:24],16)<2**33)  # address word
    cand=[(int(x,16),i) for i,x in enumerate(w) if i>bi and 1<int(x,16)<2**48]
    if not cand: return data,None
    v,i=max(cand); w[i]=format(int(v*0.98),'064x')
    return '0x'+''.join(w), v
def probe(frm,data,C):
    j=rpc('eth_call',[{'from':frm,'to':MORPHO,'data':data,'gas':'0x7a120'},'latest'])
    if 'result' in j: return 'LIQ'
    e=j.get('error',{})
    de=e.get('data','') if isinstance(e,dict) else ''
    sel=de[:10] if isinstance(de,str) and len(de)>=10 else ''
    if sel==HP: return 'HP'
    if sel==DP: return 'DP'
    return 'OTHER'   # plain revert / ERC20 allowance failure = past the health check
out=[]
for C,tx,note in CAPS:
    t0=time.time()
    tr=subprocess.run(['fork','trace','base',tx],capture_output=True,text=True)
    txt=tr.stdout or tr.stderr
    d=json.loads(txt[txt.find('{'):])
    r=find_morpho(d.get('calls',[]), d.get('to'))
    if not r: out.append({'block':C,'error':'no morpho call'}); continue
    frm,data,morpho_err=r
    data,debt=patch(data)
    row={'block':C,'note':note,'wrapper':frm,'debt':debt,'probes':{}}
    for k in LADDER:
        subprocess.run(['fork','reset','base',str(C-k)],capture_output=True,text=True)
        row['probes'][k]=probe(frm,data,C)
        if row['probes'][k]=='HP': break
    out.append(row); print(json.dumps(row),flush=True)
    print('elapsed',round(time.time()-t0,1),file=sys.stderr,flush=True)
json.dump(out,open('/srv/farm/ws/scratch/mb-windows2.json','w'),indent=1)
