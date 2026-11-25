import json, subprocess, sys
RPC=['python3','/srv/farm/ws/tools/rpc.py','bsc']
F='0x2f8a339b5889ffac4c5a956787cda593b3c36867'
TOPIC_BID='0x8eda72ced8404ff0ffda416826fcbaed9d7326fbbc62f3bfbfb3b048f8bfe481'
TOPIC_TRUST='0x7e8e2491200fd9e2cf2541c7229d5bf89f4da14659c18fc31054176c339e310b'
TOPIC_TRANSFER='0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
def rpc(method, params):
    out=subprocess.run(RPC+[method, json.dumps(params)], capture_output=True, text=True)
    if out.returncode!=0: raise RuntimeError(out.stderr[-300:])
    return json.loads(out.stdout)['result']
def b(x): return int(x,16)
head=b(rpc('eth_blockNumber',[]))
hts=b(rpc('eth_getBlockByNumber',[hex(head),False])['timestamp'])
start_ts=hts-7*86400
# binary search boundary
lo,hi=head-1_500_000,head
while lo+2000<hi:
    mid=(lo+hi)//2
    ts=b(rpc('eth_getBlockByNumber',[hex(mid),False])['timestamp'])
    if ts<start_ts: lo=mid
    else: hi=mid
start=lo
print(f'head {head} ts {hts}; 7d boundary ~{start} ts<{start_ts}', flush=True)
CH=5000
logs={'bid':[], 'trust':[]}
ctrl_transfer=0
calls=0
fr=start
while fr<=head:
    to=min(fr+CH-1,head)
    r=rpc('eth_getLogs',[{"fromBlock":hex(fr),"toBlock":hex(to),"address":F,"topics":[[TOPIC_BID,TOPIC_TRUST]]}])
    calls+=1
    for L in r:
        logs['bid' if L['topics'][0]==TOPIC_BID else 'trust'].append((b(L['number']),L['transactionHash'],L['topics'],L['data']))
    fr=to+CH
# control: Transfer topic, same shape, last 3 chunks
fr=max(start,head-3*CH)
while fr<=head:
    to=min(fr+CH-1,head)
    r=rpc('eth_getLogs',[{"fromBlock":hex(fr),"toBlock":hex(to),"address":F,"topics":[[TOPIC_TRANSFER]]}])
    ctrl_transfer+=len(r)
    calls+=1
    fr=to+CH
print(f'chunks calls {calls}; bid logs {len(logs["bid"])}; trusted fill logs {len(logs["trust"])}; control Transfer(last 3 chunks) {ctrl_transfer}')
for k in ('bid','trust'):
    for blk,tx,tp,data in logs[k][:10]:
        print(k, blk, tx, [t[:10] for t in tp], data[:66])
