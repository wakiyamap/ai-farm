import json, subprocess
ORCL={'cbBTC':'0x663becd10dae6c4a3dcd89f1d76c1174199639b9',
 'cbETH':'0x97ff9cbd7e77348b2b8ffbb883bf29452ad18295',
 'cbXRP':'0x031b2efc8d70042ac8d9f5c793c4149ec4b60fde',
 'JitoSOL':'0x78f772f5fcc03256260cc1165e34da9bb3f9be1c'}
MID={'cbBTC':'0x9103c3b4e834476c9a62ea009ba2c884ee42e94e6e314a26f04d312434191836',
 'cbETH':'0x0ca10126f6c94cbd9cf0a48cc9516ae5e3dec5aa68303e6d988ee37c5149bf0d',
 'cbXRP':'0xd4a903dc6d949519060c7707f9604fdc9772c046e05c2e3a8fce0bd7196e4109',
 'JitoSOL':'0x09276541cfecb6920a80679a1deced4dde3ae64bf5fc2c9c1f9c21e0c152e1a5'}
def rpc(method, params):
    p=subprocess.run(['python3','tools/rpc.py','base',method,json.dumps(params)],capture_output=True,text=True)
    if not p.stdout: return {}
    return json.loads(p.stdout)
def lq(sql):
    p=subprocess.run(['ledger','query','--json',sql],capture_output=True,text=True)
    return [json.loads(l) for l in p.stdout.splitlines() if l.strip()]
# assemble sample: top-5 overall gross (cbBTC) + top-4 cbXRP + top-3 cbETH + top-2 JitoSOL (spot-priced ranking)
P={'cbBTC':(1e8,58077.77),'cbETH':(1e18,1650.94),'cbXRP':(1e6,0.9014),'JitoSOL':(1e9,68.64)}
sample=[]
for k,n in (('cbBTC',6),('cbXRP',4),('cbETH',3),('JitoSOL',2)):
    d,p=P[k]
    q=f"SELECT tx_hash, block, ts, json_extract(fields,'$.caller') caller, CAST(json_extract(fields,'$.repaidAssets') AS INTEGER) repaid, CAST(json_extract(fields,'$.seizedAssets') AS INTEGER) seized, '{k}' mk FROM events WHERE chain='base' AND source_id='morpho_blue.liquidate' AND ts>=1794656520 AND json_extract(fields,'$.id')='{MID[k]}' ORDER BY (CAST(json_extract(fields,'$.seizedAssets') AS REAL)/{d:.0f}*{p} - CAST(json_extract(fields,'$.repaidAssets') AS REAL)/1e6) DESC LIMIT {n}"
    sample+=lq(q)
# faab example
q="SELECT tx_hash, block, ts, json_extract(fields,'$.caller') caller, CAST(json_extract(fields,'$.repaidAssets') AS INTEGER) repaid, CAST(json_extract(fields,'$.seizedAssets') AS INTEGER) seized, 'cbBTC' mk FROM events WHERE chain='base' AND source_id='morpho_blue.liquidate' AND tx_hash='0x7985c0f1c327e012d96387f1ca7d21ee45d8d2ea43e1185e8be93fcce48251e4' LIMIT 1"
sample+=lq(q)
# feeds
feeds={}
for k,o in ORCL.items():
    r=rpc('eth_call',[{'to':o,'data':'0xf50a4718'},'latest']).get('result')
    feeds[k]='0x'+r[-40:] if r else None
txs=sorted(set(e['tx_hash'] for e in sample)); blocks=sorted(set(int(e['block']) for e in sample))
rc={}; bf={}
for t in txs:
    r=rpc('eth_getTransactionReceipt',[t]).get('result')
    if r: rc[t]=r
for b in blocks:
    r=rpc('eth_getBlockByNumber',[hex(b),False]).get('result')
    if r: bf[b]=int(r['baseFeePerGas'],16)
# n_liq per tx
nliq={}
ql="SELECT tx_hash, COUNT(*) n FROM events WHERE chain='base' AND source_id='morpho_blue.liquidate' AND ts>=1794656520 AND tx_hash IN (%s) GROUP BY tx_hash" % (','.join("'%s'"%t for t in txs))
for r in lq(ql): nliq[r['tx_hash']]=int(r['n'])
rows=[]
for e in sample:
    b=int(e['block']); m=e['mk']
    pr=rpc('eth_call',[{'to':ORCL[m],'data':'0xa035b1fe'},hex(b-1)]).get('result')
    price=int(pr,16) if pr else None
    gross=(e['seized']*price/1e36-e['repaid'])/1e6 if price else None
    upd=None
    f=feeds.get(m)
    if f:
        r=rpc('eth_call',[{'to':f,'data':'0xfeaf968c'},hex(b-1)]).get('result')
        if r and len(r)>=258: upd=int(r[130:170],16)
    btt=(int(e['ts'])-upd)/0.2 if upd else None
    r=rc.get(e['tx_hash'])
    pf=None; gasu=None; eff=None
    if r:
        eff=int(r['effectiveGasPrice'],16); gasu=int(r['gasUsed'],16)
        pf=(eff-bf.get(b,0))/1e9
    n=nliq.get(e['tx_hash'],1)
    rows.append(dict(m=m,tx=e['tx_hash'][:14],blk=b,ts=e['ts'],caller=e['caller'][:12],
      gross_oracle=round(gross,2) if gross is not None else None,
      gross_spot=round(e['seized']/P[m][0]*P[m][1]-e['repaid']/1e6,2),
      blocks_to_taken=round(btt,1) if btt is not None else None, feed_upd=upd,
      prio_gwei=round(pf,4) if pf is not None else None, gas_per_liq=gasu//n,
      nliq=n, gas_usd=round(gasu/n*eff/1e9*ETH/1.0 if False else gasu/n*eff/1e18*1650.94,4)))
json.dump(rows, open('scratch/m356_rows.json','w'), indent=1)
for r in rows: print(json.dumps(r))
