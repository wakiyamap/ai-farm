import json, subprocess
ORCL={'cbBTC':'0x663becd10dae6c4a3dcd89f1d76c1174199639b9',
 'cbETH':'0x97ff9cbd7e77348b2b8ffbb883bf29452ad18295',
 'cbXRP':'0x031b2efc8d70042ac8d9f5c793c4149ec4b60fde',
 'JitoSOL':'0x78f772f5fcc03256260cc1165e34da9bb3f9be1c'}
def rpc(method, params):
    p=subprocess.run(['python3','tools/rpc.py','base',method,json.dumps(params)],capture_output=True,text=True)
    if not p.stdout: return {}
    return json.loads(p.stdout)
feeds={}
for k,o in ORCL.items():
    r=rpc('eth_call',[{'to':o,'data':'0xf50a4718'},'latest']).get('result')
    feeds[k]='0x'+r[-40:] if r else None
rows=json.load(open('scratch/m356_rows.json'))
seen={}
for r in rows:
    f=feeds.get(r['m'])
    if not f: continue
    key=(r['m'],r['blk'])
    if key not in seen:
        res=rpc('eth_call',[{'to':f,'data':'0xfeaf968c'},hex(r['blk']-1)]).get('result')
        # latestRoundData: roundId, answer, startedAt, updatedAt, answeredInRound -> word 3
        seen[key]=int(res[2+96:2+128],16) if res and len(res)>=2+160 else None
    upd=seen[key]
    r['feed_upd']=upd
    r['blocks_to_taken']=round((int(r['ts'])-upd)/0.2,1) if upd else None
    print(r['m'], r['tx'], r['blk'], 'upd', upd, 'blocks_to_taken', r['blocks_to_taken'])
json.dump(rows, open('scratch/m356_rows.json','w'), indent=1)
b=rpc('eth_getBlockByNumber',['latest',False]).get('result')
print('latest baseFee gwei', int(b['baseFeePerGas'],16)/1e9)
