import json, urllib.request, os, sys
RELAY=os.environ['RPC_RELAY_URL']
def call(chain, method, params, lane='research'):
    body=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    req=urllib.request.Request(f"{RELAY}/{chain}?lane={lane}", data=body, headers={"content-type":"application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        d=json.loads(r.read().decode())
    if 'error' in d: raise RuntimeError(json.dumps(d['error'])[:300])
    return d['result']

T0="0x0143172ff1dd87f3691e870b3fb5616db820278d26d2d16c3e03330a240a6c38"
CH={
 "opmainnet":("optimism","0x94460443Ca27FFC1baeCa61165fde18346C91AbD"),
 "polygon":("polygon","0xa59FfbB55D91Fc32b44A06F0b9cc6036a4afbcE2"),
 "bsc":("bsc","0xa59FfbB55D91Fc32b44A06F0b9cc6036a4afbcE2"),
 "base":("base","0xff77c0ed0b6b13a20446969107e5867abc46f53a"),
}
DAYS=int(sys.argv[1]) if len(sys.argv)>1 else 30
SECS={'opmainnet':1,'polygon':2.1,'bsc':0.9,'base':2.0}
out={}
for k,(chain,addr) in CH.items():
    head=int(call(chain,'eth_blockNumber',[]),16)
    span=int(DAYS*86400/SECS[k])
    lo=head-span
    # split in chunks <=600k blocks
    logs=[]
    a=lo
    step=600000
    reqs=0
    while a<=head:
        b=min(a+step-1,head)
        try:
            res=call(chain,'eth_getLogs',[{"address":addr,"topics":[T0],"fromBlock":hex(a),"toBlock":hex(b)}])
            logs.extend(res)
        except RuntimeError as e:
            logs.append({"scan_error":str(e)[:150]})
        reqs+=1
        a=b+1
    rec={}
    for lg in logs:
        if isinstance(lg,dict) and lg.get('recipient') is None and 'scan_error' in lg: pass
        if 'topics' in lg:
            r=int(lg['topics'][1],16) if len(lg['topics'])>1 else 0
            rn="0x%040x"%r if r else None
            rec[rn]=rec.get(rn,0)+1
    out[k]={"head":head,"blocks_scanned":span,"n_logs":len(logs),"recipients":rec,"requests":reqs}
    print(k,out[k])
json.dump(out,open('scratch/fee-release-census.json','w'),indent=1)
