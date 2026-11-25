exec(open('scratch/research25-measure.py').read().split('rows=json')[0])
samples=json.load(open('scratch/research25-samples.json'));out=[]
for q in samples[:4]+samples[-2:]:
 r=rpc('debug_traceTransaction',[q['tx'],{'tracer':'callTracer'}]);out.append({'tx':q['tx'],'response':r})
 print(q['tx'],str(r)[:120])
open('scratch/research25-traces.json','w').write(json.dumps(out))
