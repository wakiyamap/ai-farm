import json, urllib.request, os
URL=os.environ['RPC_RELAY_URL']+'/ethereum?lane=research'
def rpc(m,p):
    b=json.dumps({"jsonrpc":"2.0","id":1,"method":m,"params":p}).encode()
    r=json.loads(urllib.request.urlopen(urllib.request.Request(URL,b,{'content-type':'application/json'}),timeout=60).read())
    if 'error' in r: print(m,'ERR',r['error']); return None
    return r['result']
def bal(tok,h,dec):
    d='0x70a08231'+tok[2:].lower().rjust(64,'0') if False else '0x70a08231'+h[2:].lower().rjust(64,'0')
    v=rpc('eth_call',[{'to':tok,'data':d},'latest'])
    return int(v or '0x0',16)/10**dec
toks={'MRVEL':'0xf404e5f887dbd5508e16a1198fcdd5de1a4296b8','VST':'0xf1573edddb75bf7ce165f142a17ed6b5e7f5aa13','Oklo':'0xf0372e226553af4f343b44111a789f87a9fa427a','Broadcom':'0x0d54d4279b9e8c54cd8547c2c75a8ee81a0bcae8','CoreWeave':'0x66908813cd7676269494b2c6f6dbab8b4f9e95df'}
usdc='0xA0b86991c6218a36c1da1f9d27862fefc60e1fef'.lower()
holders={'incumbent':'0x492a0579a866e1830bdec8756789d0b2645586b9','bidder2':'0xc0ffeebabe5d496b2dde509f9fa189c25cf29671','bidder3':'0x00aa588bbb6f48005198b6d4a699107542566970'}
out={}
for name,h in holders.items():
    res={'USDC':round(bal(usdc,h,6),2)}
    for t,a in toks.items(): res[t]=round(bal(a,h,18),4)
    out[name]=res
print(json.dumps(out,indent=1))
json.dump(out,open('scratch/dtf91-bal.json','w'),indent=1)
