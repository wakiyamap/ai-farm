import json,sys
d=json.load(open(sys.argv[1]))
d=d.get('result',d)
def w(c,dep=0):
    inp=c.get('input','')
    print('  '*dep+f"{c.get('type')} {c.get('from','')[:10]}->{c.get('to','')} sel={inp[:10]} len={len(inp)//2} gas={int(c.get('gasUsed','0x0'),16)} {'ERR '+c.get('error','') if c.get('error') else ''} out={c.get('output','')[:74]}")
    if dep<int(sys.argv[2]) :
        for s in c.get('calls',[]): w(s,dep+1)
w(d)
