import json, collections
DEC = {'0x82af49447d8a07e3bd95bd0d56f35241523fbab1':('WETH',18),'0xaf88d065e77c8cc2239327c5edb3a432268e5831':('USDC',6),
'0x2f2a2543b76a4166549f7aab2e75bef0aefc5b0f':('WBTC',8),'0xfd086bc7cd5c481dcc9c85ebe478a1c0b69fcbb9':('USDT',6),
'0xff970a61a04b1ca14834a43f5de4533ebddb5cc8':('USDCe',6),'0xda10009cbd5d07dd0cecc66161fc93d7c9000da1':('DAI',18),
'0x912ce59144191c1204e64559fe8253a0e49e6548':('ARB',18),'0x5979d7b546e38e414f7e9822514be443a4800529':('wstETH',18),
'0xd22a58f79e9481d1a88e00c343885a588b34b68b':('EURS',2),'0x35751007a407ca6feffe80b3cb397736d2cf4dbe':('weETH',18),
'0x93b346b6bc2548da6a1e7d98e9a421b42541425b':('LUSD',18),'0xba5ddd1f9d7f570dc94a51479a000e3bce967196':('AAVE',18)}
PX = {'WETH':1821.41,'ETH':1821.41,'USDC':0.99979,'USDCe':0.9998,'USDT':0.9991,'DAI':0.99994,'ARB':0.132584,
'wstETH':2274.85,'EURS':1.10219,'weETH':2009.97,'WBTC':65023.65,'LUSD':1.00273,'AAVE':107.948}
ETH_PX = 1821.41

events=[]
for line in open('scratch/lead9-events.jsonl'):
    r=json.loads(line); f=json.loads(r['fields'])
    c=DEC[f['collateralAsset'].lower()]; d=DEC[f['debtAsset'].lower()]
    cq=int(f['liquidatedCollateralAmount'])/10**c[1]; dq=int(f['debtToCover'])/10**d[1]
    gross=cq*PX[c[0]]-dq*PX[d[0]]
    events.append(dict(block=r['block'],tx=r['tx_hash'],ts=r['ts'],user=f['user'],liq=f['liquidator'],
        coll=c[0],debt=d[0],same=c[0]==d[0],gross=gross,debt_usd=dq*PX[d[0]],coll_usd=cq*PX[c[0]]))
print(f"events: {len(events)}  distinct tx: {len(set(e['tx'] for e in events))}  distinct users: {len(set(e['user'] for e in events))}")

# receipts
gasinfo={}
for line in open('scratch/lead9-receipts.tsv'):
    tx,blk,raw=line.rstrip('\n').split('\t',2)
    o=json.loads(raw)['result']
    gasinfo[tx]=dict(eff=int(o['effectiveGasPrice'],16),used=int(o['gasUsed'],16),
        l1=int(o.get('gasUsedForL1','0x0'),16),frm=o['from'],status=o['status'])

base={}
for line in open('scratch/lead9-blocks.tsv'):
    b,hexb,raw=line.rstrip('\n').split('\t',2)
    blkres=json.loads(raw)['result']
    base[int(b)]=int(blkres['baseFeePerGas'],16)

# per-tx aggregation
txs=collections.defaultdict(list)
for e in events: txs[e['tx']].append(e)
rows=[]
for tx,evs in txs.items():
    g=gasinfo.get(tx)
    b=evs[0]['block']
    bf=base.get(b)
    pf=(g['eff']-bf) if (g and bf is not None) else None
    gross_usd=sum(e['gross'] for e in evs)
    gas_eth=g['used']*g['eff']/1e18 if g else None
    rows.append(dict(tx=tx,block=b,ts=evs[0]['ts'],n=len(evs),liq=evs[0]['liq'],frm=g['frm'] if g else None,
        eff=g['eff'] if g else None,priority=pf,used=g['used'] if g else None,
        gas_usd=gas_eth*ETH_PX if gas_eth else None,gross=gross_usd,
        same=all(e['same'] for e in evs),status=g['status'] if g else None))
rows.sort(key=lambda r:-r['gross'])
print(f"capture txs: {len(rows)}  failed: {sum(1 for r in rows if r['status']!='0x1')}")
print("\nTop 20 by gross USD:")
for r in rows[:20]:
    pf = f"{r['priority']/1e9:.4f}" if r['priority'] is not None else '?'
    print(f"blk {r['block']} tx {r['tx'][:16]} liq {r['liq'][:12]} frm {r['frm'][:12] if r['frm'] else '?'} n={r['n']} same={r['same']} gross=${r['gross']:.2f} gas=${r['gas_usd']:.3f} prio={pf}gwei used={r['used']}")
paid=[r for r in rows if r['gross']>0]
print(f"\ntxs with gross>0: {len(paid)}  gross>gas: {sum(1 for r in rows if r['gross'] and r['gas_usd'] and r['gross']>r['gas_usd'])}")
print(f"total gross: {sum(r['gross'] for r in rows):.2f} USD, total gas paid: {sum(r['gas_usd'] or 0 for r in rows):.2f} USD")
# winners who took gross>1 events
big=[r for r in rows if r['gross']>1]
print(f"\noccurrences gross>1 USD: {len(big)}")
for r in big:
    print(f"  blk {r['block']} {r['tx'][:20]} gross ${r['gross']:.2f} gas ${r['gas_usd']:.3f} net ${r['gross']-r['gas_usd']:.2f} liq {r['liq']}")
# priority fee stats
pfs=sorted(r['priority'] for r in rows if r['priority'] is not None)
import statistics
print(f"\npriority fee gwei: n={len(pfs)} min {pfs[0]/1e9:.6f} med {statistics.median(pfs)/1e9:.4f} max {pfs[-1]/1e9:.4f}")
bfs=sorted(base.values()); print(f"block base fee gwei (capture blocks): min {bfs[0]/1e9:.6f} med {statistics.median(bfs)/1e9:.6f} max {bfs[-1]/1e9:.6f}")
us=sorted(r['used'] for r in rows if r['used']); print(f"gasUsed: min {us[0]} med {statistics.median(us):.0f} p90 {us[int(len(us)*0.9)]} max {us[-1]}")
json.dump(rows,open('scratch/lead9-rows.json','w'))
