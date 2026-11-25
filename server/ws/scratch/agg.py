import json, glob, os
ETH=1822.304131
P={'0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48':(6,0.9997892),
   '0xdac17f958d2ee523a2206206994597c13d831ec7':(6,0.99901),
   '0x40d16fc0246ad3160ccc09b8d0d3a2cd28ae6c2f':(18,0.9984515),
   '0x4c9edd5852cd905f086c759e8383e09bff1e68b3':(18,0.9995594),
   '0x18084fba666a33d37592fa2633fd49a74dd93a88':(18,64624.05),
   '0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2':(18,1822.304),
   '0x2260fac5e5542a773aa44fbcfedf7c193bc2c599':(8,64819.66),
   '0x7f39c581f595b53c5cb19bd0b3f8da6c935e2ca0':(18,2212.0),
   '0x7fc66500c84a76ad7e9c93437bfc5ac33e2ddae9':(18,109.966),
   '0x6b175474e89094c44da98b954eedeac495271d0f':(18,1.0),
   '0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee':(18,1822.304)}
def usd(a,v):
    a=a.lower(); d,p=P.get(a,(18,0.0))
    return int(v)/10**d*p
rows=[]
for line in open('scratch/aave_ev.jsonl'):
    r=json.loads(line); f=json.loads(r['fields'])
    rows.append((r['tx_hash'], r['block'], usd(f['debtAsset'],f['debtToCover']), usd(f['collateralAsset'],f['liquidatedCollateralAmount'])))
import collections
txs=collections.OrderedDict()
for h,b,d,c in rows:
    t=txs.setdefault(h,{'block':b,'n':0,'debt':0.0,'coll':0.0})
    t['n']+=1; t['debt']+=d; t['coll']+=c
tot_gas=0; print('%-20s %7s %3s %10s %10s %9s %8s'%('tx','block','n','debtUSD','collUSD','grossUSD','gasUSD'))
for h,t in txs.items():
    fn='scratch/rcs/%s.json'%h
    g=None
    if os.path.exists(fn):
        rr=json.load(open(fn))['result']
        g=int(rr['gasUsed'],16)*int(rr['effectiveGasPrice'],16)/1e18*ETH
        tot_gas+=g
    print('%-20s %7d %3d %10.2f %10.2f %9.2f %8s'%(h[:18],t['block'],t['n'],t['debt'],t['coll'],t['coll']-t['debt'], ('%.2f'%g) if g is not None else 'n/a'))
print('AAVE totals: txs %d liq %d debtUSD %.0f collUSD %.0f gross %.2f gasUSD %.2f'%(len(txs),sum(t['n'] for t in txs.values()),sum(t['debt'] for t in txs.values()),sum(t['coll'] for t in txs.values()),sum(t['coll']-t['debt'] for t in txs.values()),tot_gas))
