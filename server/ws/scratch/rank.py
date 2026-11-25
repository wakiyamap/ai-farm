import sys, json; sys.path.insert(0,'/srv/farm/ws/scratch')
pairs=json.load(open('/srv/farm/ws/scratch/uv2opt_reserves.json'))
dec=json.load(open('/srv/farm/ws/scratch/uv2opt_decimals.json'))
pr=json.load(open('/srv/farm/ws/scratch/uv2opt_prices.json'))
def val(t,r):
    d=dec.get(t); p=pr.get(t)
    if d is None or p is None or r==0: return 0.0
    return r/(10**d)*p
for p in pairs:
    p['usd']=val(p['token0'],p['r0'])+val(p['token1'],p['r1'])
pairs.sort(key=lambda p:-p['usd'])
tot=sum(p['usd'] for p in pairs)
print('census priced TVL total USD %.0f' % tot)
for p in pairs[:20]:
    print('%10.2f  %s  t0=%s r0=%.4f  t1=%s r1=%.4f  ts=%d' % (
        p['usd'], p['pair'], p['token0'][:10], p['r0']/10**(dec[p['token0']] or 0),
        p['token1'][:10], p['r1']/10**(dec[p['token1']] or 0), p['ts']))
json.dump(pairs[:300], open('/srv/farm/ws/scratch/uv2opt_top.json','w'))
