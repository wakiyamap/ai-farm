import json, urllib.request, os, collections
URL=os.environ['RPC_RELAY_URL']
def rpc(method, params, chain='ethereum', lane='research'):
    body=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    req=urllib.request.Request(f"{URL}/{chain}?lane={lane}", data=body, headers={'content-type':'application/json'})
    return json.loads(urllib.request.urlopen(req, timeout=90).read())['result']
CRV="0xd533a949740bb3306d119cc777fa900ba034cd52"
HEAD=26372987
rec=collections.Counter()
tot=0
for i in range(5):
    to=HEAD-i*2000; frm=to-1999
    logs=rpc("eth_getLogs",[{"address":CRV,"topics":[None,None,"0x"+"0"*24+"f"*22,"0x"+"0"*64],"fromBlock":hex(frm),"toBlock":hex(to)}])
    tot+=len(logs)
    for l in logs:
        v=int.from_bytes(bytes.fromhex(l['data'][2:]),'big')
        if v>=10**17:  # >=1e5 CRV (18dec)
            r=l['topics'][3][26:]; rec["0x"+r]+=1
print("big CRV recipient-counts (>=1e5 tokens) over 10k blocks:", tot, "big events")
for k,v in rec.most_common(25): print(k,v)
