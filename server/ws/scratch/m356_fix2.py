import json, subprocess
FEED={'cbBTC':'0x663becd10dae6c4a3dcd89f1d76c1174199639b9','cbETH':'0x97ff9cbd7e77348b2b8ffbb883bf29452ad18295','cbXRP':'0x031b2efc8d70042ac8d9f5c793c4149ec4b60fde','JitoSOL':'0x78f772f5fcc03256260cc1165e34da9bb3f9be1c'}
def rpc(method, params):
    p=subprocess.run(['python3','tools/rpc.py','base',method,json.dumps(params)],capture_output=True,text=True)
    return json.loads(p.stdout) if p.stdout else {}
# BASE_FEED_1 addresses per oracle
bf={}
for k,o in FEED.items():
    r=rpc('eth_call',[{'to':o,'data':'0xf50a4718'},'latest']).get('result')
    bf[k]='0x'+r[-40:] if r else None
print(bf)
rows=json.load(open('scratch/m356_rows.json'))
seen={}
for r in rows:
    f=bf.get(r['m'])
    if not f: continue
    key=(r['m'],r['blk'])
    if key not in seen:
        res=rpc('eth_call',[{'to':f,'data':'0xfeaf968c'},hex(r['blk']-1)]).get('result')
        seen[key]=int(res[194:258],16) if res and len(res)>=258 else None
    upd=seen[key]
    r['feed_upd']=upd
    r['blocks_to_taken']=round((int(r['ts'])-upd)/0.2,1) if upd else None
    print(r['m'], r['tx'], r['blk'], 'upd', upd, 'btt', r['blocks_to_taken'])
json.dump(rows, open('scratch/m356_rows.json','w'), indent=1)
import statistics as st
g=[r['gross_oracle'] for r in rows if r['gross_oracle'] is not None]
p=[r['prio_gwei'] for r in rows if r['prio_gwei'] is not None]
b=[r['blocks_to_taken'] for r in rows if r['blocks_to_taken'] is not None]
print('median gross_oracle', st.median(g), 'median prio gwei', st.median(p), 'median btt', st.median(b), 'btt max', max(b))
