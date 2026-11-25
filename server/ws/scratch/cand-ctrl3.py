import json, urllib.request, os, collections
URL=os.environ['RPC_RELAY_URL']
def rpc(method, params, chain='ethereum', lane='research'):
    body=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    req=urllib.request.Request(f"{URL}/{chain}?lane={lane}", data=body, headers={'content-type':'application/json'})
    d=json.loads(urllib.request.urlopen(req, timeout=120).read())
    return d.get('result', 'ERR:'+str(d.get('error',{}).get('message')))
CAND="0xb576491f1e6e5e62f1d8f26062ee822b40b0e0d4"; CRV="0xd533a949740bb3306d119cc777fa900ba034cd52"
HEAD=26372987
logs=rpc("eth_getLogs",[{"address":CRV,"fromBlock":hex(HEAD-2000),"toBlock":hex(HEAD)}])
print('all CRV transfers last 2000 blocks:', len(logs))
rec=collections.Counter(l['topics'][2][26:] for l in logs)
print('top recipients:', rec.most_common(8))
print('candidate count in window:', rec.get(CAND[2:],0))
# positive control for recipient filter: same filter shape, known recipient from top list
k="0x"+rec.most_common(1)[0][0]
l2=rpc("eth_getLogs",[{"address":CRV,"topics":[None,None,"0x"+"0"*24+k[2:]],"fromBlock":hex(HEAD-2000),"toBlock":hex(HEAD)}])
print('control filter for', k, '->', len(l2), 'events')
l3=rpc("eth_getLogs",[{"address":CRV,"topics":[None,None,"0x"+"0"*24+CAND[2:]],"fromBlock":hex(HEAD-2000),"toBlock":hex(HEAD)}])
print('candidate filter same window ->', len(l3) if l3 is not None else l3)
