import json,sys
d=json.load(open(sys.argv[1]))
d=d.get('result',d)
maxd=int(sys.argv[2]) if len(sys.argv)>2 else 4
def w(c,dep):
    if dep>maxd: return
    inp=c.get('input','')
    print('  '*dep+f"{c['type']} {c.get('from','')[:8]}->{c.get('to','')} {inp[:10]} len={len(inp)//2} gas={int(c.get('gasUsed','0x0'),16)} v={int(c.get('value','0x0'),16)} {'ERR '+c.get('error','') if c.get('error') else ''}")
    for s in c.get('calls',[]): w(s,dep+1)
w(d,0)
