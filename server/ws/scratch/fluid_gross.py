import json, collections, statistics
logs=json.load(open('/srv/farm/ws/scratch/inwin.json'))
P={'WBTC':62651.9548512,'USDT0':0.99892,'USDC':0.9998789427,'WSTETH':2196.074920223408,'POL':0.08030736945}
DEC={'0xdf16adaf80584b2723f3ba1eb7a601338ba18c4e':('WBTC','USDT0',8,6),
     '0xf55b8e9f0c51ace009f4b41d03321675d4c643b3':('WBTC','USDC',8,6),
     '0xa0f83fc5885cebc0420ce7c7b139adc80c4f4d91':('WSTETH','USDC',18,6)}
rows=[]
for l in logs:
    d=l['data'][2:]
    w=[d[i:i+64] for i in range(0,len(d),64)]
    liq='0x'+w[0][-40:]
    col=int(w[1],16); debt=int(w[2],16)
    v=l['address'].lower()
    if v in DEC:
        cs,ds,cd,dd=DEC[v]
        g=col/10**cd*P[cs]-debt/10**dd*P[ds]
    else:
        g=None
    rows.append(dict(v=v[:10],blk=int(l['blockNumber'],16),tx=l['transactionHash'],liq=liq,col=col,debt=debt,gross=g,ts=int(l['blockTimestamp'],16)))
paid=[r for r in rows if r['gross'] is not None]
print('priced',len(paid),'unpriced(0xf2c8f544)',len(rows)-len(paid))
paid.sort(key=lambda r:-r['gross'])
print('top 10 gross:')
for r in paid[:10]:
    print('  {:8.2f}  {} blk {} {} liq 0x{}'.format(r['gross'], r['v'], r['blk'], r['tx'][:14], r['liq'][-8:]))
neg=[r for r in paid if r['gross']<0]
print('negative gross count:',len(neg),'min',round(min((r['gross'] for r in paid),default=0),2))
gs=[r['gross'] for r in paid]
print('median gross all priced:',round(statistics.median(gs),2))
pos=[g for g in gs if g>0]
print('paid>0 count:',len(pos),'median paid:',round(statistics.median(pos),2))
json.dump(rows,open('/srv/farm/ws/scratch/rows90.json','w'))
