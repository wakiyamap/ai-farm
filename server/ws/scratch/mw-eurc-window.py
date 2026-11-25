import json, urllib.request, os
URL=os.environ['RPC_RELAY_URL']
CMP="0xfbb21d0380bee3312b33c4353c8936a0f13ef26c"; SEL="0x5ec88c79"
def call(to,data,block):
    p={"jsonrpc":"2.0","id":1,"method":"eth_call","params":[{"to":to,"data":data},hex(block)]}
    rq=urllib.request.Request(f"{URL}/base?lane=research",data=json.dumps(p).encode(),headers={"content-type":"application/json"})
    r=json.loads(urllib.request.urlopen(rq,timeout=90).read())
    if 'error' in r: print("ERR",r['error'],hex(block)); return None
    return r['result']
def cls(w):
    v=int(w,16); return 'LIQ' if (v>>254) else 'OK'
EVENTS=[(54697042,'0x1e61f524d60e77e58119a24fadd3ff8b0732caa6','one-off whale 86.61 EURC'),
        (55046981,'0x33a7ec1055edd4cc35ef289156c7a7a078043474','repeat-default 66.14 EURC'),
        (55076179,'0x33a7ec1055edd4cc35ef289156c7a7a078043474','repeat-default 6.29 EURC')]
out=[]
for c,h,lbl in EVENTS:
    d=8
    w=call(CMP,SEL+h[2:].rjust(64,'0'),c-d)
    if w is None: out.append({'block':c,'err':1}); continue
    rec={'block':c,'holder':h[:10],'label':lbl,'liq8':cls(w)=='LIQ'}
    if rec['liq8']:
        last=c-8
        for d in [16,32,64,128,256,512,1024,2048,4096,8192,16384,32768]:
            w2=call(CMP,SEL+h[2:].rjust(64,'0'),c-d)
            if w2 is None: break
            if cls(w2)=='LIQ': last=c-d
            else: rec['crossing_block']=c-d; break
        rec['window_blocks_min']=c-last
    else:
        w3=call(CMP,SEL+h[2:].rjust(64,'0'),c-2)
        rec['liq2']=cls(w3)=='LIQ' if w3 else None
        rec['window_blocks_min']=0 if rec['liq2'] is None else (2 if rec['liq2'] else None)
    out.append(rec); print(json.dumps(rec))
json.dump(out,open('scratch/mw-eurc-window.json','w'),indent=1)
