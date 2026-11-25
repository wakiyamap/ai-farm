import json, urllib.request, os
RELAY=os.environ['RPC_RELAY_URL']
def call(chain, method, params, lane='research'):
    body=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    req=urllib.request.Request(f"{RELAY}/{chain}?lane={lane}", data=body, headers={"content-type":"application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        d=json.loads(r.read().decode())
    if 'error' in d: raise RuntimeError(json.dumps(d['error'])[:300])
    return d['result']
T0="0x0143172ff1dd87f3691e870b3fb5616db820278d26d2d16c3e03330a240a6c38"
CH={"opmainnet":("optimism","0x94460443Ca27FFC1baeCa61165fde18346C91AbD"),
    "polygon":("polygon","0xa59FfbB55D91Fc32b44A06F0b9cc6036a4afbcE2"),
    "bsc":("bsc","0xa59FfbB55D91Fc32b44A06F0b9cc6036a4afbcE2")}
SECS={"opmainnet":1,"polygon":2.1,"bsc":0.9}
out={}
for k,(chain,addr) in CH.items():
    head=int(call(chain,'eth_blockNumber',[]),16)
    lo=head-int(30*86400/SECS[k]); logs=[]; a=lo
    while a<=head:
        b=min(a+600000-1,head)
        logs.extend(call(chain,'eth_getLogs',[{"address":addr,"topics":[T0],"fromBlock":hex(a),"toBlock":hex(b)}]))
        a=b+1
    rec={}
    rows=[]
    for lg in logs:
        rn=int(lg['topics'][1],16)
        r="0x"+lg['topics'][2][26:].lower()
        rec[r]=rec.get(r,0)+1
        rows.append({"block":int(lg['blockNumber'],16),"tx":lg['transactionHash'],"nonce":rn,"recipient":r})
    out[k]={"n":len(logs),"recipients":rec,"events":rows}
    print(k,len(logs),rec)
json.dump(out,open('scratch/fee-release-census2.json','w'),indent=1)
