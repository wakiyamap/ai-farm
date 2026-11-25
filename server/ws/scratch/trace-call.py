import json, urllib.request, os
url = os.environ['DSH_FORK_URL'] if 'DSH_FORK_URL' in os.environ else 'http://127.0.0.1:9003'
def rpc(m,p):
    b=json.dumps({'jsonrpc':'2.0','id':1,'method':m,'params':p}).encode()
    return json.load(urllib.request.urlopen(urllib.request.Request(url,data=b,headers={'content-type':'application/json'}),timeout=90))
OWNER='0x1111111111111111111111111111111111111111'
EXEC='0x8f7a45ebde059392e46a46dcc14ab24681a961ea'
USDC='0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48'
OVAULT='0x8aC6AD5D76D07B202832f323888B64286E944A9e'
allow='0x'+'dd258f9c'+'000000000000000000000000'+OWNER[2:]+'000000000000000000000000'+EXEC[2:]
r=rpc('eth_call',[{'from':OWNER,'to':USDC,'data':allow},'latest'])
print('allowance owner->executor', r)
print('balance owner', int(rpc('eth_call',[{'from':OWNER,'to':USDC,'data':'0x70a08231'+OWNER[2:]},"latest"])['result'],16))
print('owner==executor owner() ', int(rpc('eth_call',[{'to':EXEC,'data':'0x8da5cb5b'},'latest'])['result'],16))
dep='0x'+'e2bbb158'+'000000000000000000000000017d167c'+'000000000000000000000000017d167c'
r=rpc('debug_traceCall',[{'from':OWNER,'to':EXEC,'data':dep},'latest',{'tracer':'callTracer'}])
d=r.get('result') or {}
print('top err', d.get('err'), d.get('error'))
def walk(c,depth=0):
    print(' '*depth, c.get('type'), (c.get('from') or '')[:10],'->',(c.get('to') or '')[:10], c.get('err') or c.get('error') or '', (c.get('function') or ''))
    for s in c.get('calls',[]) or []: walk(s,depth+1)
walk(d)
