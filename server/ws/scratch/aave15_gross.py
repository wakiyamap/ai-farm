import json
P = {
 '0x2f2a2543b76a4166549f7aab2e75bef0aefc5b0f':(65264.657,8,'WBTC'),
 '0x35751007a407ca6feffe80b3cb397736d2cf4dbe':(2014.964,18,'weETH'),
 '0x5979d7b546e38e414f7e9822514be443a4800529':(2271.128,18,'wstETH'),
 '0x82af49447d8a07e3bd95bd0d56f35241523fbab1':(1825.778,18,'WETH'),
 '0x912ce59144191c1204e64559fe8253a0e49e6548':(0.1317,18,'ARB'),
 '0x93b346b6bc2548da6a1e7d98e9a421b42541425b':(1.0028,18,'LUSD'),
 '0xaf88d065e77c8cc2239327c5edb3a432268e5831':(0.99991,6,'USDC'),
 '0xba5ddd1f9d7f570dc94a51479a000e3bce967196':(108.0832,18,'AAVE'),
 '0xda10009cbd5d07dd0cecc66161fc93d7c9000da1':(0.9998,18,'DAI'),
 '0xfd086bc7cd5c481dcc9c85ebe478a1c0b69fcbb9':(0.9993,6,'USDT0'),
 '0xff970a61a04b1ca14834a43f5de4533ebddb5cc8':(0.99968,6,'USDCe'),
}
rows=[]
for line in open('scratch/aave15_rows.jsonl'):
    line=line.strip()
    if not line: continue
    r=json.loads(line)
    c=r['c'].lower(); d=r['d'].lower()
    lca=int(r['lca']); dtc=int(r['dtc'])
    if c in P and d in P:
        pc,dc,_=P[c]; pd,dd,_=P[d]
        cv=lca/(10**dc)*pc; dv=dtc/(10**dd)*pd
        r['coll_usd']=cv; r['debt_usd']=dv; r['gross']=cv-dv
        r['bonus_pct']=(cv/dv-1)*100 if dv>0 else None
    else:
        r['gross']=None
    rows.append(r)
priced=[r for r in rows if r['gross'] is not None]
priced.sort(key=lambda r:r['gross'], reverse=True)
print(f"total {len(rows)}, priced {len(priced)}, unpriced {len(rows)-len(priced)}")
print("\n=== TOP 8 by gross (USD, current prices) ===")
for r in priced[:8]:
    print(f"gross=${r['gross']:.2f}  coll=${r['coll_usd']:.0f} debt=${r['debt_usd']:.0f} bonus={r['bonus_pct']:.2f}% blk={r['block']} liq={r['liq'][:10]} tx={r['tx_hash'][:12]}")
print("\n=== gross distribution (priced) ===")
import statistics
gs=[r['gross'] for r in priced]
for q in [50,75,90,95,99]:
    print(f"p{q} = ${statistics.quantiles(gs,n=100)[q-1]:.2f}")
print(f"median gross = ${statistics.median(gs):.2f}  mean = ${statistics.mean(gs):.2f}  max = ${max(gs):.2f}")
print(f"bonus_pct median = {statistics.median([r['bonus_pct'] for r in priced]):.2f}%")
# how many have gross> some gas thresholds
for g in [0.5,1.0]:
    print(f"gross > ${g}: {sum(1 for x in gs if x>g)} of {len(gs)}")
