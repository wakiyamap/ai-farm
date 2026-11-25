import json, urllib.request, os, collections, sys
URL=os.environ['RPC_RELAY_URL']; LANE='research'
def rpc(m,p=None,i=1):
    b=json.dumps({"jsonrpc":"2.0","id":i,"method":m,"params":p if p is not None else []}).encode()
    req=urllib.request.Request(f"{URL}/elysium?lane={LANE}",b,{"content-type":"application/json"})
    r=json.loads(urllib.request.urlopen(req,timeout=60).read())
    if 'error' in r: raise SystemExit(f"{m}: {json.dumps(r['error'])}")
    return r['result']
T0="0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
head=int(rpc("eth_blockNumber"),16)
fr=hex(head-1200); logs=rpc("eth_getLogs",[{"address":"0xb47c4C8F73F009CC0C0d3f92B388d13E293F0B65","topics":[T0],"fromBlock":fr,"toBlock":hex(head)}])
cnt=collections.Counter()
for l in logs:
    for t in l['topics'][1:]:
        cnt['0x'+t[-40:].lower()]+=1
print(f"head={head} usdc_logs={len(logs)} distinct={len(cnt)}")
for a,c in cnt.most_common(16): print(a,c)
