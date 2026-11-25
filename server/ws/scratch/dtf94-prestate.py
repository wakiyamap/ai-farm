import json,os,urllib.request
url=os.environ.get('RPC_RELAY_URL'); lane='research'
def rpc(method,params):
    body=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    req=urllib.request.Request(f"{url}/{os.environ.get('RPC_CHAIN','ethereum')}?lane={lane}",data=body,headers={"content-type":"application/json"})
    return json.loads(urllib.request.urlopen(req,timeout=120).read())
r=rpc("debug_traceTransaction",["0x773a7b4c03f31d849210ff3f7c5b19a2c79c0b7c4736b20df57cddc74fa871e6",{"tracer":"prestateTracer","tracerConfig":{"diffMode":True}}])
open('scratch/dtf94-prestate.json','w').write(json.dumps(r))
res=r.get('result',{})
pre=res.get('pre',{});post=res.get('post',{})
def bal(d,addr,key):
    a=d.get(addr,{}); v=a.get(key or 'balance')
    return int(v,16) if isinstance(v,str) else v
CSCO='0x0d54d4279b9e8c54cd8547c2c75a8ee81a0bcae8';MRVEL='0xf404e5f887dbd5508e16a1198fcdd5de1a4296b8'
FILLER='0xd98d34008d1bbb29013592c637f8e9fca4179fa0';WINNER='0x223add4afe4cc7de41d8c17e0c96926cda6d2015'
USDC='0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48'
print('keys in pre sample', list(pre.items())[:1][0] if pre else None)
def tok(d,addr,slot=None):
    a=d.get('0x'+addr[2:] if addr in d else addr,{})
    return a
for addr,name in ((CSCO,'CSCO'),(MRVEL,'MRVEL'),(FILLER,'FILLER'),(WINNER,'winnerEOA'),(USDC,'USDC')):
    print(name, 'native', bal(pre,addr,'balance'),'->',bal(post,addr,'balance'))
def enc(slot): 
    h=hex(slot)[2:].rjust(64,'0'); return h
for addr,name,slot in ((CSCO,'CSCO',1),(MRVEL,'MRVEL',1)):
    pass
