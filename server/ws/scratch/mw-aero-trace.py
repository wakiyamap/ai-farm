import json,urllib.request,os,re
URL=os.environ['RPC_RELAY_URL']+'/base?lane=research'
def req(m,p):
    rq=urllib.request.Request(URL,data=json.dumps({"jsonrpc":"2.0","id":1,"method":m,"params":p}).encode(),headers={"content-type":"application/json"})
    return json.loads(urllib.request.urlopen(rq,timeout=120).read())
r=req('debug_traceTransaction',['0xf0579b9d69c3712b5ddbdc91b033e98bf4ff3714702232d003d772258bbc2f55',{"tracer":"callTracer"}])
res=r.get('result') or {}
open('scratch/mw-aero-trace.json','w').write(json.dumps(res))
def walk(f,d=0):
    to=f.get('to'); si=f.get('input','')
    if to:
        print(' '*d, to[:12]+'…', si[:10], f.get('type','')[:6], 'gasUsed', f.get('gasUsed'))
    for c in f.get('calls',[]): walk(c,d+2)
walk(res)
