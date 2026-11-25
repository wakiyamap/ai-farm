import json, urllib.request, os
URL=os.environ['RPC_RELAY_URL']
def rpc(method, params, chain='ethereum', lane='research'):
    body=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    req=urllib.request.Request(f"{URL}/{chain}?lane={lane}", data=body, headers={'content-type':'application/json'})
    return json.loads(urllib.request.urlopen(req, timeout=120).read())['result']
def trace(h):
    r=rpc("debug_traceTransaction",[h,{"tracer":"callTracer"}])
    return r
def flat(d, depth=0, out=None):
    out=[]
    def rec(c, exdata=None):
        out.append((c.get('from'),c.get('to'),(c.get('input') or '')[:10],c.get('type'),c.get('value'),len(c.get('calls',[]))))
        for s in c.get('calls',[]): rec(s)
    rec(d)
    return out
for label,h in [('keep1','0x6638e88c6c41c37cef74a63781dd48b1bd4e0b34c79f3571b17d172387b7bdc8'),
                ('sec1','0xd74fde9d31efc9b299af5518fdac58718c7ee469b5f5157745b257f3273718b0')]:
    r=trace(h)
    print(label, r['to'], r['from'], (r['input'] or '')[:10], r['type'])
    rows=flat(r)
    seen=set()
    for row in rows[:60]:
        k=(row[0],row[1],row[2])
        if k in seen: continue
        seen.add(k)
        print(row)
    json.dump(r, open(f'scratch/mower-tr-{label}.json','w'))
