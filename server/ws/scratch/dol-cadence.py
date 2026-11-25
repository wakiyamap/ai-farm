import json, urllib.request, os
url=os.environ['RPC_RELAY_URL']
def post(chain, lane, method, params):
    req={"jsonrpc":"2.0","id":1,"method":method,"params":params}
    r=urllib.request.urlopen(f"{url}/{chain}?lane={lane}", json.dumps(req).encode(), timeout=30)
    return json.loads(r.read())['result']
head=26357859; span=259200  # 30 d
lo=head-span+1
topic="0x1b9e65b359b871d74b1af1fc8b13b11635bfb097c4631b091eb762fda7e67dc7"
events=[]
pages=0
b=lo
while b<=head:
    e=min(b+29999,head)
    r=post("ethereum","research","eth_getLogs",[{"address":"0x003Ca23Fd5F0ca87D01F6eC6CD14A8AE60c2b97D","topics":[topic],"fromBlock":hex(b),"toBlock":hex(e)}])
    events+=r; pages+=1
    b=e+1
out=[]
for l in events:
    blk=int(l['blockNumber'],16)
    d=l['data']; words=[int(d[i:i+64],16) for i in range(0,len(d),64)]
    # data words: [number, borrower, asset, deltaDebt?, ...] - interest-like words are ~4.5e74; debt/coll deltas are <1e22 or 6dec
    deltas=[w for w in words if 1e7<w<1e22]  # raw debt/coll values (18dec up to 1e4 USD or 6dec)
    out.append({'blk':blk,'tx':l['transactionHash'][:10],'acct':l['topics'][1][26:46],'words':words})
json.dump(out, open('scratch/dol-cadence.json','w'))
print(pages,'pages,',len(events),'events over', span,'blocks (30 d)')
