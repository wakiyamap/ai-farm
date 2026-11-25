import json
exec(open('scratch/aave15_gross.py').read().split('rows=[]')[0])  # reuse P
rows=[]
for line in open('scratch/aave15_rows.jsonl'):
    line=line.strip()
    if not line: continue
    r=json.loads(line)
    c=r['c'].lower(); d=r['d'].lower()
    lca=int(r['lca']); dtc=int(r['dtc'])
    if c in P and d in P:
        pc,dc,_=P[c]; pd,dd,_=P[d]
        r['coll_usd']=lca/10**dc*pc; r['debt_usd']=dtc/10**dd*pd
        r['gross']=r['coll_usd']-r['debt_usd']; r['bonus_pct']=(r['coll_usd']/r['debt_usd']-1)*100
        r['csym']=P[c][2]; r['dsym']=P[d][2]
    else: r['gross']=None
    rows.append(r)
priced=[r for r in rows if r['gross'] is not None]
priced.sort(key=lambda r:r['gross'], reverse=True)
top5=priced[:5]
rest=priced[5:]
# pick 15 spanning sorted-by-gross list
idxs=[round(i*(len(rest)-1)/14) for i in range(15)]
others=[rest[i] for i in idxs]
sample=top5+others
# dedup keep order
seen=set(); samp=[]
for r in sample:
    k=r['tx_hash']
    if k in seen: continue
    seen.add(k); samp.append(r)
with open('scratch/aave15_sample.json','w') as f:
    json.dump(samp,f)
print(f"sample size {len(samp)} (top5 + {len(samp)-5} others)")
for r in samp:
    print(f"blk={r['block']} gross=${r['gross']:.2f} bonus={r['bonus_pct']:.1f}% {r['csym']}->{r['dsym']} liq={r['liq']} tx={r['tx_hash']}")
