import json,subprocess,collections
A='0xd38a5a7c3cec073884be9561b12d327236bde02f'
def rpc(method,params):
 p=subprocess.run(['python3','/srv/farm/ws/tools/rpc.py','hyperevm',method,json.dumps(params)],capture_output=True,text=True)
 if p.returncode: raise RuntimeError(p.stderr+p.stdout)
 return json.loads(p.stdout)['result']
q={'fromBlock':hex(51482971),'toBlock':'latest','fromAddress':A,'category':['external'],'withMetadata':True,'excludeZeroValue':False,'maxCount':'0x3e8'}
all=[]
while True:
 r=rpc('alchemy_getAssetTransfers',[q]);all+=r.get('transfers',[])
 if not r.get('pageKey'):break
 q['pageKey']=r['pageKey']
print(json.dumps({'n':len(all),'by_to':dict(collections.Counter(t['to'].lower() for t in all)),'first':all[0]['hash'] if all else None,'last':all[-1]['hash'] if all else None,'pageKey':bool(r.get('pageKey'))}))
print(json.dumps([{'h':t['hash'],'b':int(t['blockNum'],16),'to':t['to']} for t in all if t['to'].lower()=='0x1b8e94763019968d1a3b8d586c5ef96d8ac3a9f6']))
