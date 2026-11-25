import json, subprocess, time
NODE="https://polygon.drpc.org"
VAULT="0xdf16adaf80584b2723f3ba1eb7a601338ba18c4e"
DATA="0x8433ea22"+hex(10**30)[2:].rjust(64,'0')+"0"*64+"dead".rjust(64,'0')+"0"*64
def call(blk,to=VAULT):
    body=json.dumps({"jsonrpc":"2.0","id":1,"method":"eth_call","params":[{"to":to,"data":DATA},hex(blk)]})
    for a in range(3):
        p=subprocess.run(["curl","-s","-m","40","-H","Content-Type: application/json","-X","POST",NODE,"-d",body],capture_output=True,text=True)
        try: d=json.loads(p.stdout)
        except Exception: time.sleep(1); continue
        if "error" in d:
            e=d["error"]
            if e.get("code")==3 or "revert" in str(e.get("message","")).lower():
                dt=str(e.get("data") or "")
                return "REV", dt
            time.sleep(1); continue
        return "OK", str(d["result"])
    return "FAIL", ""
w=json.load(open('/srv/farm/ws/scratch/trial-fluid-polygon/windows.json'))
wtx={e['tx'] for e in w}
rows=json.load(open('/srv/farm/ws/scratch/rows90.json'))
sample=[]
paid=[r for r in rows if r['gross'] is not None]
paid.sort(key=lambda r:-r['gross'])
top5=paid[:5]
# spread: 4 new Nov12/13 events, 2 exceptions, 2 f2c8f544, wsteth+wbtcusdc, 6 mid/low builder positives
exc=[r for r in paid if r['tx'] in ('0xb9ede7c51037','0x2f12dfbf8373') or r['blk'] in (97281172,97325778)]
new=[r for r in rows if r['tx'] not in wtx][:3]+[r for r in rows if r['tx'] not in wtx][8:10]
misc=[r for r in rows if r['tx'] not in wtx][:1]
ws=[r for r in paid if r['v']=='0xa0f83fc5'][:1]
wu=[r for r in paid if r['v']=='0xf55b8e9f'][:1]
f2c=[r for r in rows if r['v']=='0xf2c8f544'][:2]
mid=[r for r in paid if r['gross'] is not None and 0<r['gross']<24][:6]
seen=set(); sample=[]
for r in top5+exc+new+ws+wu+f2c+mid:
    if r['tx'] in seen: continue
    seen.add(r['tx']); sample.append(r)
sample=sample[:20]
print("sample",len(sample))
out=[]
for r in sample:
    st1,m1=call(r['blk']-1, r['v'] if r['v']!='0xf2c8f54' else VAULT)
    delta=None
    code1=m1[-64:] if m1 and m1!='None' else ''
    if st1=="REV":
        delta=0  # not takeable at -1 (verify code convention below)
        if code1:
            try: delta={"0"*63+"1":0,"0"*63+"0":0}.get(code1,('CODE',int(code1,16)))
            except Exception: pass
    elif st1=="OK":
        delta=None
    out.append(dict(r, probe=st1, code=m1[-12:] if st1=='REV' else m1))
    print(r['blk'], r['v'], round(r['gross'],2) if r['gross'] is not None else 'n/a', st1, (m1[-12:] if st1=='REV' else m1[:40]))
json.dump(out, open('/srv/farm/ws/scratch/sample_probe.json','w'))
