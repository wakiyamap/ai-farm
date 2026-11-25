import json, urllib.request, os
URL=os.environ['RPC_RELAY_URL']; LANE='research'
def rpc(method,params=[]):
    p={"jsonrpc":"2.0","id":1,"method":method,"params":params}
    rq=urllib.request.Request(f"{URL}/base?lane={LANE}",data=json.dumps(p).encode(),headers={"content-type":"application/json"})
    return json.loads(urllib.request.urlopen(rq,timeout=90).read()).get('result')
head=int(rpc("eth_blockNumber"),16)
FEED="0xec942be8a8114bfd0396a5052c36027f2ca6a9d0"
for span in (40000, 130000):
    L=rpc("eth_getLogs",[{"address":FEED,"fromBlock":hex(head-span),"toBlock":hex(head)}])
    if L is None: print('logs err'); break
    blocks=[int(x['blockNumber'],16) for x in L]
    gaps=sorted(b2-b1 for b1,b2 in zip(blocks,blocks[1:]))
    print(span, 'feeder logs:', len(L), 'median gap blocks:', gaps[len(gaps)//2] if gaps else None, 'max gap:', gaps[-1] if gaps else None)
    if len(L)<2000: break
