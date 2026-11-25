import json,subprocess,collections
A='0xd38a5a7c3cec073884be9561b12d327236bde02f'
def rpc(method,params):
 p=subprocess.run(['python3','/srv/farm/ws/tools/rpc.py','hyperevm',method,json.dumps(params)],capture_output=True,text=True)
 if p.returncode: raise RuntimeError(p.stderr+p.stdout)
 return json.loads(p.stdout)['result']
q={'fromBlock':hex(51482971),'toBlock':'latest','fromAddress':A,'category':['external'],'withMetadata':True,'excludeZeroValue':False,'maxCount':'0x3e8'}
t=rpc('alchemy_getAssetTransfers',[q])['transfers']
for dest in ['0xd83fba56076f8e603e0aa52d7c73741253208e1b','0xc4a1daae467f59301c34ba55420c32a8438648c2','0x8b363fcb41f16be532d4d17d52cabbed5adc76d6','0x84a9ae54edace6716043ba40eb69f8825f2e2dea']:
 h=next(x['hash'] for x in reversed(t) if x['to'].lower()==dest)
 tx=rpc('eth_getTransactionByHash',[h]);r=rpc('eth_getTransactionReceipt',[h])
 out=[]
 for l in r['logs']:
  if len(l['topics'])==3 and l['topics'][0]=='0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef':
   fr='0x'+l['topics'][1][-40:];to='0x'+l['topics'][2][-40:]
   if fr.lower()==dest or to.lower()==dest:out.append({'token':l['address'],'from':fr,'to':to,'amount':int(l['data'],16)})
 print(json.dumps({'h':h,'dest':dest,'block':int(r['blockNumber'],16),'selector':tx['input'][:10],'status':int(r['status'],16),'gas':int(r['gasUsed'],16),'gasHype':int(r['gasUsed'],16)*int(r['effectiveGasPrice'],16)/1e18,'transfers':out}))
