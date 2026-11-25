import json,urllib.request,subprocess,sys
F='http://127.0.0.1:9001'
def rpc(m,p):
    d=json.dumps({"jsonrpc":"2.0","id":1,"method":m,"params":p}).encode()
    r=urllib.request.urlopen(urllib.request.Request(F,d,{'content-type':'application/json'}))
    j=json.load(r)
    if 'result' not in j: raise Exception(str(j["error"])[:150])
    return j['result']
MORPHO='0xbbbbbbbbbb9cc5e90e3b3af64bdaf62c37eeffcb'
MULTI='0xca11bde05977b3631167028862be2a173976ca11'
def addr(a): return a[2:].lower().rjust(64,'0')
def encCalls(calls):
    import math
    def ru(n): return -(-n//32)*32
    starts=[];acc=0x20*len(calls)
    for c in calls: starts.append(acc); acc+=0x60+ru((len(c['data'])-2)//2)
    enc='bce38bd7'+ '0'*63+'1'+'0'*63+'40'+format(len(calls),'064x')
    for i in range(len(calls)): enc+=format(starts[i],'064x')
    for c in calls:
        dl=(len(c['data'])-2)//2
        enc+=addr(c['to'])+'0'*63+'40'+format(dl,'064x')+c['data'][2:]+'0'*(ru(dl)*2-(len(c['data'])-2))
    return '0x'+enc
def dec(h):
    h=h[2:]; base=64; n=int(h[base:base+64],16); out=[]
    for i in range(min(n,3)):
        es=base+64+int(h[base+64+i*64:base+128+i*64],16)*2
        succ=int(h[es:es+64],16)!=0
        off=int(h[es+64:es+128],16); ln=int(h[es+off*2:es+off*2+64],16)
        rd=h[es+off*2+64:es+off*2+64+ln*2]
        out.append({'success':succ,'rd':'0x'+rd})
    return out
params=json.load(open('scratch/mb157-params.json'))
sel={r['block']:r for r in json.load(open('scratch/mb157-sel.json'))}
caps=[56245267,56242285,56160199,55986767,55691587,55675682,55690698,56232054]
res=[]
for C in caps:
    row=sel[C]; mid=row['mkt']; p=params[mid]
    subprocess.run(['fork','reset','base',str(C-1)],stdout=open('/dev/null','w'))
    tag='0x'+hex(C-1)[2:]
    mp=addr(p['loan'])+addr(p['coll'])+addr(p['oracle'])+addr(p['irm'])+format(p['lltv'],'064x')
    _rp=rpc('eth_call',[{'to':MORPHO,'data':'0x151c1ade'+mp},tag]) # accrue first: accrues totals in the tag's simulation context; market read after
    d=rpc('eth_call',[{'to':MORPHO,'data':'0x5c60e39a'+mid[2:]},tag])[2:]
    tBA=int(d[128:192],16); tBS=int(d[192:256],16)
    price=int(rpc('eth_call',[{'to':p['oracle'],'data':'0xa035b1fe'},tag]),16)
    rs=int(row['rs']); sa=int(row['sa'])
    vS=tBS+10**6
    debt=(rs*(tBA+1)+vS-1)//vS  # toAssetsUp
    def md(c): return ( (c*price//10**36) * p['lltv'] )//10**18
    md_lo=md(sa); md_hi=md(sa + (sa*3)//7)  # collateral after seize in [0, 0.4286*sa]
    cls = 'liquidatable_at_C-1' if debt>md_hi else ('healthy_at_C-1' if debt<=md_lo else 'ambiguous')
    res.append({'C':C,'mkt':mid[:16],'debt':debt,'ra':row['ra'],'rs':rs,'sa':sa,
        'price':price,'md_lo':md_lo,'md_hi':md_hi,'cls':cls})
    print(json.dumps(res[-1]))
json.dump(res,open('scratch/mb157-hfbound.json','w'),indent=1)
