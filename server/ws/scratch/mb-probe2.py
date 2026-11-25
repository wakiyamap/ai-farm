import json, urllib.request, subprocess, sys, time
MORPHO='0xbbbbbbbbbb9cc5e90e3b3af64bdaf62c37eeffcb'
FORK='http://127.0.0.1:9001'
HP='0x52a528df'   # HEALTHY_POSITION()
OTHERS={'DEBT':'0x20c61c89','I':'0xd7260006','TF':'0x2c863d26'}
READS={'0x70a08231','0xa9059cbb','0x23b872dd','0xdd62ed3e','0x5c60da1b','0xfeaf968c','0xf69058c1','0x6eb71926','0x67c572ea','0x0709a8d6','0x313ce567','0x06fdde03','0x95d8c686','0x1816f495','0x095ea7b3','0x8b5c8df5','0xdde5345c'}
CAPS=[
 (56265482,'0x4dc2631721bb8a491e7e43524c171d6f84346f7657a18a09de088b107ad2a0f8'),
 (56160131,'0x097700d317198cd643ae9c0b292a5f0b100ffb023f2fc2ec7ee3d2a3a8465990'),
 (56160094,'0x3ce651419c3814376194aad7297bd79ade07bf053b07d696f413f2b61d47bdd6'),
 (56160057,'0xd49d07fcdb55494b23d5e35881ff016484e95dbf84811ed525fc411c09172a10'),
 (55951354,'0x13bf67e4131714f36bc24283bd1d8ef95d1471303661d022d32de2b62f74cf4e'),
 (55945504,'0x3123d163c83b64ce22a863a3cd32987f1cda888c2c299af3177389dc2e6bb5b8'),
 (56245267,'0x8840c48bd2f5905d655f27f1af822d12d0d75959b56efb6f6a5c52efb0eba02f'),
 (56374332,'0xf1c68254b2fa683151032b2bb8c3ebbd74746057baa224dc5be8aee088dbc81c'),
]
LADDER=[1,8,32,128,512]  # blocks before capture
def rpc(method,params):
    body=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    req=urllib.request.Request(FORK,body,{'content-type':'application/json'})
    return json.loads(urllib.request.urlopen(req,timeout=30).read())
def find_morpho(calls, parent_to):
    for c in calls:
        inp=c.get('input','')
        if c.get('to','').lower()==MORPHO and inp[:10] not in READS and len(inp)>10:
            return parent_to, inp, c.get('error')
        r=find_morpho(c.get('calls',[]), c.get('to',parent_to))
        if r: return r
    return None
out=[]
for C,tx in CAPS:
    t0=time.time()
    tr=subprocess.run(['fork','trace','base',tx],capture_output=True,text=True)
    txt=tr.stdout or tr.stderr; i=txt.find('{')
    d=json.loads(txt[i:])
    r=find_morpho(d.get('calls',[]), d.get('to'))
    if not r:
        out.append({'block':C,'error':'no morpho call found'}); continue
    frm,data,morpho_err=r
    w=[data[10+i*64:10+(i+1)*64] for i in range((len(data)-10)//64)]
    d0=int(w[2],16); d1=int(d0*0.99)
    w[2]=format(d1,'064x')
    data='0x'+w[0]+w[1]+w[2]+w[3]+''.join(w[4:])
    row={'block':C,'wrapper':frm,'morpho_err_at_C':morpho_err,'probes':{}}
    for k in LADDER:
        tag=C-k
        subprocess.run(['fork','reset','base',str(tag)],capture_output=True,text=True)
        j=rpc('eth_call',[{'from':frm,'to':MORPHO,'data':data,'gas':'0x7a120'},'latest'])
        if 'result' in j: row['probes'][k]='OK'
        elif 'error' in j:
            e=j['error']
            err=e.get('message','') if isinstance(e,dict) else str(e)
            data_err=e.get('data','') if isinstance(e,dict) else ''
            sel=data_err[:10] if isinstance(data_err,str) and len(data_err)>=10 else ''
            tag_err='HP' if sel==HP else next((n for n,s in OTHERS.items() if sel==s), ('REVERT:'+err[:30] if not sel else 'X'+sel))
            row['probes'][k]=tag_err
            if tag_err=='HP': break
    out.append(row)
    print(json.dumps(row), flush=True)
    print('C',C,'elapsed',round(time.time()-t0,1), file=sys.stderr, flush=True)
json.dump(out, open('/srv/farm/ws/scratch/mb-windows.json','w'), indent=1)
