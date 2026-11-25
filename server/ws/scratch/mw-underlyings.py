import json, urllib.request, os
URL=os.environ['RPC_RELAY_URL']; LANE='research'
def call(to,data,tag='latest'):
    p={"jsonrpc":"2.0","id":1,"method":"eth_call","params":[{"to":to,"data":data},tag]}
    rq=urllib.request.Request(f"{URL}/base?lane={LANE}",data=json.dumps(p).encode(),headers={"content-type":"application/json"})
    r=json.loads(urllib.request.urlopen(rq,timeout=60).read())
    return r.get('result') or ('ERR '+json.dumps(r.get('error')))
def logs(addr, frm, to):
    p={"jsonrpc":"2.0","id":1,"method":"eth_getLogs","params":[{"address":addr,"fromBlock":hex(frm),"toBlock":hex(to)}]}
    rq=urllib.request.Request(f"{URL}/base?lane={LANE}",data=json.dumps(p).encode(),headers={"content-type":"application/json"})
    r=json.loads(urllib.request.urlopen(rq,timeout=90).read())
    return r.get('result') or [ 'ERR '+json.dumps(r.get('error')) ]
mkts=["0x3bf93770f2d4a794c3d9ebefbaebae2a8f09a5e5","0xdc7810b47eaab250de623f0ee07764afa5f71ed1","0x703843c3379b52f9ff486c9f5892218d2a065cc8","0xfc41b49d064ac646015b459c522820db9472f4b5","0x73902f619ceb9b31fd8efecf435cbdf89e369ba6","0xb8051464c8c92209c92f3a4cd9c73746c4c3cfb3"]
SEL_UND="0x6d342007"  # underlying()
SEL_SYM="0x95d9b2ad"  # symbol()
for m in mkts:
    print(m, call(m,SEL_UND), call(m,SEL_SYM))
FEED="0xec942be8a8114bfd0396a5052c36027f2ca6a9d0"
head=int(call("0x0000000000000000000000000000000000000000","0x0", 'latest') or 0)
import urllib.request as u
h=json.loads(u.urlopen(u.Request(f"{URL}/base?lane={LANE}",data=json.dumps({"jsonrpc":"2.0","id":1,"method":"eth_blockNumber","params":[]}).encode(),headers={"content-type":"application/json"}),timeout=30).read())['result']
head=int(h,16); print('head',head)
L=logs(FEED, head-40000, head)
print('feeder logs last 40000 blocks:', len(L)-1 if L and str(L[0]).startswith('ERR') else len(L), 'cadence blocks/update:', round(40000/max(len(L),1)) )
if L and not str(L[0]).startswith('ERR') and L:
    blocks=[int(x['blockNumber'],16) for x in L]
    gaps=[b2-b1 for b1,b2 in zip(blocks,blocks[1:])]
    print('feeder update blocks span', blocks[0], blocks[-1], 'median gap', sorted(gaps)[len(gaps)//2] if gaps else None)
