import json, urllib.request, os, sys
URL=os.environ['RPC_RELAY_URL']; LANE='research'
def call(to, data, block):
    payload={"jsonrpc":"2.0","id":1,"method":"eth_call","params":[{"to":to,"data":data},"%s"%hex(block)]}
    req=urllib.request.Request(f"{URL}/base?lane={LANE}", data=json.dumps(payload).encode(), headers={"content-type":"application/json"})
    r=json.loads(urllib.request.urlopen(req, timeout=60).read())
    if 'error' in r: raise SystemExit(f"relay error: {r['error']}")
    return r['result']
CMP="0xfbb21d0380bee3312b33c4353c8936a0f13ef26c"  # core comptroller
# verify full address: search trace for 0xfbb21d prefix
import re
s=open('scratch/mw-whale-trace.json').read()
m=[a for a in set(re.findall(r'0x[0-9a-fA-F]{40}', s)) if a.lower().startswith('0xfbb21d03')]
if m: CMP=m[0].lower()
SEL="0x5ec88c79"
def probe(holder, block):
    data=SEL+holder[2:].rjust(64,'0')
    res=call(CMP, data, block)
    return res
def cls(w):
    if not w or w=='0x': return 'empty'
    v=int(w,16)
    if v >> 254: return 'LIQ'   # negative liquidity (wraparound) => liquidatable
    return 'OK'                  # healthy
events={
 'E1_53506974': (53506974,'0x893d6c896940fa58190013f4c97be56c2a7fb152'),
 'E2_53313790': (53313790,'0x689584e4a494bd3cc6c0a1ef223a103dc800b73d'),
 'E3_53519985': (53519985,'0x73ebc72977819b1735ecc4adf515e47b18970200'),
}
STEPS=[1,3,7,15,31,63,127,511,2047,8191,16383]
out={}
for name,(c,h) in events.items():
    rows=[]
    lo=None
    for d in STEPS:
        b=c-d
        if b<1: break
        try: w=probe(h,b)
        except SystemExit as e:
            rows.append({'d':d,'block':b,'err':str(e)}); break
        st=cls(w)
        rows.append({'d':d,'block':b,'w':w[:20]+('...' if len(w)>24 else ''),'st':st})
        if st=='OK': lo=b; break
        if st=='LIQ': last_liq=b
    out[name]={'capture':c,'holder':h,'rows':rows,'crossing_between':[lo,last_liq] if 'last_liq' in dir() else None}
print(json.dumps(out, indent=1))
