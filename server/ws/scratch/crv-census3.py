import json, urllib.request, os, collections
URL=os.environ['RPC_RELAY_URL']
def rpc(method, params, chain='ethereum', lane='research'):
    body=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    req=urllib.request.Request(f"{URL}/{chain}?lane={lane}", data=body, headers={'content-type':'application/json'})
    d=json.loads(urllib.request.urlopen(req, timeout=90).read())
    if 'result' not in d: print('ERR', json.dumps(d)[:160])
    return d.get('result')
CRV="0xd533a949740bb3306d119cc777fa900ba034cd52"
HEAD=26372987
rec=collections.Counter(); tot=0
for i in range(10):
    to=HEAD-i*2000; frm=to-149
    logs=rpc("eth_getLogs",[{"address":CRV,"fromBlock":hex(frm),"toBlock":hex(to)}])
    if logs is None: continue
    tot+=len(logs)
    for l in logs:
        r=l['topics'][2][26:]; rec["0x"+r]+=1
print("total CRV Transfer logs, 1500 sampled blocks:", tot)
for k,v in rec.most_common(30): print(k,v)
