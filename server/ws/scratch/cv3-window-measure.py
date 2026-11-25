import json, urllib.request, os
RELAY=os.environ['RPC_RELAY_URL']
COMETS={'0xc3d688b66703497daa19211eedff47f25384cdc3':'cUSDCv3','0x3afdc9bca9213a35503b077a6072f3d0d5ab0840':'cUSDTv3','0xa17581a9e3356d9a858b789d68b4d866e593ae94':'cWETHv3'}
AB='0x9850ab1af75177e4a9201c65a2cf7976d5d28e40ef63494b44366f86b2f9412e'
BUY='0xf891b2a411b0e66a5f0a6ff1368670fefa287a13f541eb633a386a1a9cc7046b'
def rpc(method,params):
    d=json.dumps({'jsonrpc':'2.0','id':1,'method':method,'params':params}).encode()
    r=urllib.request.urlopen(f'{RELAY}/ethereum?lane=research',data=d,timeout=60).read()
    j=json.loads(r)
    if 'error' in j: raise SystemExit('relay error '+str(j['error'])[:200])
    return j['result']
head=int(rpc('eth_blockNumber',[]),16)
def logs(topic,fromb,tob):
    return rpc('eth_getLogs',[{'address':list(COMETS),'topics':[topic],'fromBlock':hex(fromb),'toBlock':hex(tob)}])
def d2u(w): return int(w,16)
ab=[]; buy=[]; b=26295000
while b<=head:
    e=min(b+20000-1,head)
    ab+=logs(AB,b,e); buy+=logs(BUY,b,e)
    b=e+1
out=[]
for l in ab:
    data=l['data'][2:]
    out.append({'kind':'ab','block':int(l['blockNumber'],16),'comet':COMETS.get(l['address'].lower(),'?'),'absorber':l['topics'][1],'borrower':l['topics'][2],'asset':l['topics'][3][2:],'collat':d2u(data[:64]),'usdcPaid':d2u(data[64:128])})
for l in buy:
    data=l['data'][2:]
    out.append({'kind':'buy','block':int(l['blockNumber'],16),'comet':COMETS.get(l['address'].lower(),'?'),'buyer':l['topics'][1],'asset':l['topics'][2][2:],'w0':d2u(data[:64]),'w1':d2u(data[64:128])})
json.dump(out,open('scratch/cv3-window-raw.json','w'))
print('head',head,'ab',len(ab),'buy',len(buy))
