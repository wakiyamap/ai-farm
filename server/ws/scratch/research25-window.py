exec(open('scratch/research25-measure.py').read().split('rows=json')[0])
samples={q['tx']:q for q in json.load(open('scratch/research25-samples.json'))};out=[]
def walk(n):
 yield n
 for c in n.get('calls',[]):yield from walk(c)
for tr in json.load(open('scratch/research25-traces.json'))[:4]:
 q=samples[tr['tx']];r=tr['response']['result'];f=next(c for c in walk(r) if c.get('to','').lower()=='0xa2bcd1a4efbd04b63cd03f5aff2561106ebcce00' and c.get('input','').startswith('0x167f83f4'))
 price=rpc('eth_call',[{'to':'0x5f4ec3df9cbd43714fe2740f5e3616155c5b8419','data':'0xfeaf968c'},hex(q['block'])])
 v={'tx':q['tx'],'price':price,'forward':f,'probes':[]}
 for k in [1,16,64,256]:
  block=hex(q['block']-k)
  res=rpc('eth_call',[{'from':f['from'],'to':f['to'],'data':f['input'],'gas':'0x7a1200'},block]);v['probes'].append({'offset':k,'response':res})
 out.append(v)
 print(q['block'],[(x['offset'],x['response'].get('result',x['response'].get('error'))) for x in v['probes']])
open('scratch/research25-window.json','w').write(json.dumps(out,indent=2))
