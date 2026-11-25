import json, subprocess, urllib.request
toks=json.load(open('/srv/farm/ws/scratch/uv2opt_pairs_full.json'))
tokens=sorted({p['token0'] for p in toks} | {p['token1'] for p in toks})
prices={}
B=150
for i in range(0,len(tokens),B):
    ch=tokens[i:i+B]
    url='https://coins.llama.fi/prices/current/'+','.join('optimism:'+t for t in ch)
    try:
        with urllib.request.urlopen(url, timeout=60) as r: d=json.load(r)
    except Exception as ex:
        print('fail',i,ex); continue
    for k,v in d.get('coins',{}).items():
        prices['0x'+k.split(':')[-1][2:].lower() if False else '0x'+k.split(':')[1][2:].lower() if k.split(':')[1].startswith('0x') else k]=v.get('price')
    if (i//B) % 10 == 0: print(i, len(prices), flush=True)
print('priced', len(prices), 'of', len(tokens))
json.dump(prices, open('/srv/farm/ws/scratch/uv2opt_prices.json','w'))
