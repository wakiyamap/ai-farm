import subprocess, json
def rpc(method, params):
    r=subprocess.run(['python3','/srv/farm/ws/tools/rpc.py','base',method,json.dumps(params)],capture_output=True,text=True)
    try: d=json.loads(r.stdout)
    except: return None
    if 'error' in d: return None
    return d['result']
pairs=json.load(open('/tmp/ss/pairs.json'))[:10]
def call(to, data):
    res=rpc('eth_call',[{'to':to,'data':data},'latest'])
    return res
rows=[]
for p in pairs:
    t0=call(p,'0x0dfe1681'); t1=call(p,'0xd21220a7')
    if not t0 or not t1: continue
    a0=a1=0; r0=r1=0
    gr=call(p,'0x0902f1ac')
    if gr and len(gr)>=194:
        r0=int(gr[2:66],16); r1=int(gr[66:130],16)
    bal0=call('0x'+t0[-40:], '0x70a08231'+p[2:].lower().rjust(64,'0'))
    bal1=call('0x'+t1[-40:], '0x70a08231'+p[2:].lower().rjust(64,'0'))
    if bal0: a0=int(bal0,16)
    if bal1: a1=int(bal1,16)
    s0=a0-r0; s1=a1-r1
    rows.append((p, '0x'+t0[-40:], '0x'+t1[-40:], s0, s1))
    print(p, 'stranded0', s0, 'stranded1', s1, flush=True)
json.dump(rows, open('/tmp/ss/skim.json','w'))
