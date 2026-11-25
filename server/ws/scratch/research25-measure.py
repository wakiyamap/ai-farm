import requests,json,os,time,subprocess
u=os.environ['RPC_RELAY_URL']+'/ethereum?lane=research'
def rpc(m,p):
 r=requests.post(u,json={'jsonrpc':'2.0','id':1,'method':m,'params':p},timeout=45).json();return r
rows=json.load(open('scratch/research25-captures.json'))
sample=rows[:6]+sorted(rows,key=lambda x:x['block'],reverse=True)[:6]
out=[]
for x in sample:
 q=dict(x);q['transaction']=rpc('eth_getTransactionByHash',[x['tx']]);q['receipt']=rpc('eth_getTransactionReceipt',[x['tx']]);q['blockdata']=rpc('eth_getBlockByNumber',[hex(x['block']),False]);out.append(q)
open('scratch/research25-samples.json','w').write(json.dumps(out,indent=2))
for q in out:
 t=q['transaction'].get('result') or {};r=q['receipt'].get('result') or {};b=q['blockdata'].get('result') or {}
 print(q['block'],round(sum(y['usd'] for y in q['rewards']),4),t.get('from'),t.get('to'),t.get('input','')[:10],r.get('gasUsed'),r.get('effectiveGasPrice'),int(b.get('timestamp','0x0'),16))
