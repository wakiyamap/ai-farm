import json, urllib.request, os
URL=os.environ['RPC_RELAY_URL']; LANE='research'
CMP="0xfbb21d0380bee3312b33c4353c8936a0f13ef26c"; SEL="0x5ec88c79"
def call(to,data,block):
    p={"jsonrpc":"2.0","id":1,"method":"eth_call","params":[{"to":to,"data":data},hex(block)]}
    rq=urllib.request.Request(f"{URL}/base?lane={LANE}",data=json.dumps(p).encode(),headers={"content-type":"application/json"})
    r=json.loads(urllib.request.urlopen(rq,timeout=60).read())
    if 'error' in r: print("ERR",r['error']); return None
    return r['result']
def cls(w):
    v=int(w,16); return 'LIQ' if (v>>254) else 'OK'
events={
 'W4_53517746_weth83': (53517746,'0xbf65b64721cada18d23dfc68050dcdfe91fea897'),
 'W5_53342669_grind2': (53342669,'0x689584e4a494bd3cc6c0a1ef223a103dc800b73d'),
 'W6_53268172_batch': (53268172,'0x733034d9bf322ad7eb1789d7c0de1eedd5892bf6'),
 'W7_53265174_batch': (53265174,'0x78ce89c19f562f2090739015ec61da12ec26a460'),
 'W2_53489444_mid': (53489444,'0x46795203f4ce3df6c054df9231168358e2e50fd3'),
}
STEPS=[1,2,4,8,16,32,64,128,256,512,1024,2048,4096,8192]
out={}
for name,(c,h) in events.items():
    rows=[]; last_liq=None; first_ok=None
    for d in STEPS:
        b=c-d
        w=call(CMP, SEL+h[2:].rjust(64,'0'), b)
        if w is None: break
        st=cls(w)
        val=int(w,16); s=('%x'%(val>>(128 if st=='OK' else 0)))
        rows.append({'d':d,'block':b,'st':st,'val':f"{val>>20:.4e}" if st=='OK' else 'neg'})
        if st=='LIQ': last_liq=b
        else:
            first_ok=b; break
    window = (c-last_liq) if last_liq and first_ok else None
    out[name]={'capture':c,'holder':h,'ok_at_c1':rows[0]['st'],'first_ok':first_ok,'last_liq':last_liq,'window_blocks':window,'rows':rows}
print(json.dumps(out,indent=1))
