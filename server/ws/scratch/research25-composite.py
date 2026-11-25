exec(open('scratch/research25-measure.py').read().split('rows=json')[0])
samples=json.load(open('scratch/research25-samples.json'));out=[]
for q in [samples[1],samples[2],samples[-2]]:
 t=q['transaction']['result'];v={'tx':q['tx'],'probes':[]}
 for k in [1,64,256]:
  tx={x:t[x] for x in ['from','to','input','value'] if x in t};tx['data']=tx.pop('input');tx['gas']='0x989680'
  r=rpc('debug_traceCall',[tx,hex(q['block']-k),{'tracer':'callTracer'}]);v['probes'].append({'offset':k,'response':r})
  print(q['block'],k, str(r)[:120])
 out.append(v)
open('scratch/research25-composite.json','w').write(json.dumps(out))
