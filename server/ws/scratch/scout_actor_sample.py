import json,subprocess,statistics
A='0xd38a5a7c3cec073884be9561b12d327236bde02f';E='0x1b8e94763019968d1a3b8d586c5ef96d8ac3a9f6';P='0xa9dd620fc1b6316ce75c8059aaed1f5fa5e0cefb';W='0x5555555555555555555555555555555555555555'
def rpc(method,params):
 p=subprocess.run(['python3','/srv/farm/ws/tools/rpc.py','hyperevm',method,json.dumps(params)],capture_output=True,text=True)
 if p.returncode: raise RuntimeError(p.stderr+p.stdout)
 return json.loads(p.stdout)['result']
q={'fromBlock':hex(51482971),'toBlock':'latest','fromAddress':A,'category':['external'],'withMetadata':True,'excludeZeroValue':False,'maxCount':'0x3e8'}
t=[x for x in rpc('alchemy_getAssetTransfers',[q])['transfers'] if x['to'].lower()==E]
selected=t[:5]+t[-5:]
rows=[]
for x in selected:
 r=rpc('eth_getTransactionReceipt',[x['hash']]);gross=0
 for l in r['logs']:
  if l['address'].lower()==W and len(l['topics'])==3 and l['topics'][0]=='0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef' and '0x'+l['topics'][1][-40:]==E and '0x'+l['topics'][2][-40:]==P:gross+=int(l['data'],16)/1e18
 gas=int(r['gasUsed'],16)*int(r['effectiveGasPrice'],16)/1e18
 rows.append({'h':x['hash'],'b':int(r['blockNumber'],16),'status':int(r['status'],16),'grossWHYPE':gross,'gasHYPE':gas,'netUSDat64_08':(gross-gas)*64.08})
print(json.dumps(rows))
print(json.dumps({'sample':len(rows),'of':len(t),'grossWHYPE':sum(r['grossWHYPE'] for r in rows),'gasHYPE':sum(r['gasHYPE'] for r in rows),'medianGrossWHYPE':statistics.median(r['grossWHYPE'] for r in rows),'medianGasHYPE':statistics.median(r['gasHYPE'] for r in rows),'netUSDat64_08':sum(r['netUSDat64_08'] for r in rows)}))
