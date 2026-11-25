import json, os, urllib.request, time
URL=os.environ['RPC_RELAY_URL']; LANE='lane=research'
def rpc(chain, method, params):
    req=urllib.request.request if False else urllib.request
    data=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    r=urllib.request.urlopen(urllib.request.Request(f"{URL}/{chain}?{LANE}",data=data,headers={"content-type":"application/json"}),timeout=60)
    body=json.loads(r.read().decode()); 
    if 'error' in body: return {"error":body['error']}
    return body['result']
LIQ="0xa4946ede45d0c6f06a0f5ce92c9ad3b4751452d2fe0e25010783bcab57a67e41"
TRF="0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
def hexint(h): return int(h,16)
def scan(chain, lo, hi, topic, tag):
    logs=rpc(chain,"eth_getLogs",[{"fromBlock":hex(lo),"toBlock":hex(hi),"topics":[topic]}])
    if isinstance(logs,dict) and logs.get('error'): print(tag,"ERR",json.dumps(logs)[:200]); return None
    print(tag, f"{lo}-{hi}", "n_logs", len(logs), [l.get('address') for l in logs[:6]])
    return logs
out={}
for chain in ('polygon','avalanche'):
    head=hexint(rpc(chain,"eth_blockNumber",[]))
    print(chain,"head",head)
    offsets = {'polygon':[0,50000,150000,300000,500000,700000,1000000,1290000],'avalanche':[0,100000,200000,300000]}
    pagesz= 1000 if chain=='polygon' else 10000
    for off in offsets[chain]:
        lo,hi=head-off-pagesz, head-off
        logs=scan(chain,lo,hi,LIQ,f"LIQ {chain} {chain}-head-{off}")
        if logs: out.setdefault(chain,[]).append({"off":off,"logs":logs})
    # control: Transfer topic-only on the head page
    scan(chain, head-pagesz, head, TRF, f"CTRL Transfer {chain}")
    time.sleep(0.2)
json.dump({k:[{"off":x["off"],"addrs":sorted(set(l['address'] for l in x['logs'])),"n":len(x['logs'])} for x in v] for k,v in out.items()}, open('scratch/morpho-scout-hits.json','w'), indent=1)
print(open('scratch/morpho-scout-hits.json').read())
