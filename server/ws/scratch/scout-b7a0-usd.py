import json, subprocess, collections, urllib.request, datetime
FILLER='0xb7a0d4608cd7831102498f0c49a8212cfd32ee9b'
TR='0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
BNB=589.4054376
def rpc(m,p):
    r=subprocess.run(['python3','/srv/farm/ws/tools/rpc.py','bsc',m,json.dumps(p),'--lane','research'],capture_output=True,text=True)
    return json.loads(r.stdout)['result']
rows=subprocess.run(['ledger','query','--json',"SELECT block, tx_hash, ts FROM events WHERE chain='bsc' AND source_id='uniswapx.fill' AND actor='%s' ORDER BY block DESC LIMIT 30" % FILLER],capture_output=True,text=True).stdout
evs=[json.loads(l) for l in rows.strip().split('\n') if l.strip()]
recs=[]
toks=set()
for e in evs[:16]:
    rc=rpc('eth_getTransactionReceipt',[e['tx_hash']]); tx=rpc('eth_getTransactionByHash',[e['tx_hash']])
    net=collections.defaultdict(int)
    for x in rc['logs']:
        if x['topics'][0]==TR and len(x['topics'])==3:
            a=x['address'].lower(); f_='0x'+x['topics'][1][-40:].lower(); t_='0x'+x['topics'][2][-40:].lower()
            v=int(x['data'],16) if x['data']!='0x' else 0
            if f_==FILLER: net[a]-=v
            if t_==FILLER: net[a]+=v
    gas_usd=int(rc['gasUsed'],16)*int(rc['effectiveGasPrice'],16)/1e18*BNB
    toks.update([k for k,v in net.items() if v])
    recs.append({'tx':e['tx_hash'],'blk':e['block'],'ts':e['ts'],'gas_usd':gas_usd,'net':{k:v for k,v in net.items() if v},'nlogs':len(rc['logs']),'from':tx['from']})
# batch price
ids=','.join('bsc:'+t for t in toks)
u='https://coins.llama.fi/prices/current/'+ids
d=json.load(urllib.request.urlopen(u))['coins']
tot=0; vals=[]
for r in recs:
    usd=0
    for t,v in r['net'].items():
        c=d.get('bsc:'+t) or {}
        dec=c.get('decimals'); p=c.get('price')
        if dec is None or p is None: print('NO PRICE',t); continue
        usd += v/10**dec*p
    r['residual_usd']=usd; vals.append(usd); tot+=usd
    print(json.dumps({'tx':r['tx'][:14],'blk':r['blk'],'utc':datetime.datetime.fromtimestamp(r['ts'],datetime.UTC).strftime('%m-%d %H:%M'),'gas_usd':round(r['gas_usd'],4),'residual_usd':round(usd,4),'nlogs':r['nlogs'],'from':r['from'][:10],'toks':len(r['net'])}))
vals.sort()
import statistics
print('SAMPLE n=%d  median residual USD %.4f  mean %.4f  sum %.4f  gas median USD %.4f  sum gas %.4f'%(len(vals), statistics.median(vals), statistics.mean(vals), tot, statistics.median([r['gas_usd'] for r in recs]), sum(r['gas_usd'] for r in recs)))
print('min %.4f max %.4f  negative count %d'%(min(vals),max(vals),sum(1 for v in vals if v<0)))
print('tokens priced:', {t[:10]: (d['bsc:'+t]['symbol'], d['bsc:'+t]['decimals']) for t in sorted(toks) if 'bsc:'+t in d})
