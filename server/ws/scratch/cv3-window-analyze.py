import json
raw=json.load(open('scratch/cv3-window-raw.json'))
A={ '0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2':'WETH','0x2260fac5e5542a773aa44fbcfedf7c193bc2c599':'WBTC','0x1f9840a85d5af5bf1d1762f925bdaddc4201f984':'UNI','0x514910771af9ca656af840dff83e8264ecf986ca':'LINK','0xdac17f958d2ee523a2206206994597c13d831ec7':'USDT','0xc00e94cb662c3520282e6f5717214004a7f26888':'LINKv1'}
ab=[r for r in raw if r['kind']=='ab']; buys=[r for r in raw if r['kind']=='buy']
# cross-check decode orientation on the 26342224 buy (known baseAmount 110020324384802098030)
for r in buys:
    if r['block']==26342224: print('BUY decode check: w0',r['w0'],'w1',r['w1'])
for r in buys:
    if r['block']==26342225: print('BUY+1 block: w0',r['w0'],'w1',r['w1'])
# pair: for each (comet,asset) timeline in block order
from collections import defaultdict
tl=defaultdict(list)
for r in sorted(raw,key=lambda x:x['block']):
    tl[(r['comet'],r['asset'])].append(r)
print()
for k,seq in tl.items():
    print('===',k[0],A.get(k[1],k[1][:6]))
    res=0
    for r in seq:
        if r['kind']=='ab':
            res+=r['collat']
            print(f"  AB  @{r['block']} collat={r['collat']} usdcPaid={r['usdcPaid']}")
        else:
            print(f"  BUY @{r['block']} buyer={r['buyer'][:10]} w0={r['w0']} w1={r['w1']} resid_after={res}")
            res-=r['w0'] if r['w0']<r['w1'] else r['w1']  # orientation decided after check
