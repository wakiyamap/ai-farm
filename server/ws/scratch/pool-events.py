import json, urllib.request, os, collections
URL=os.environ['RPC_RELAY_URL']
def rpc(method, params, chain='ethereum', lane='research'):
    body=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    req=urllib.request.Request(f"{URL}/{chain}?lane={lane}", data=body, headers={'content-type':'application/json'})
    d=json.loads(urllib.request.urlopen(req, timeout=120).read())
    if 'result' not in d: print('ERR', json.dumps(d)[:200])
    return d.get('result')
POOL="0xcf50b810e57ac33b91dcf525c6ddd9881b139332"; CRV="0xd533a949740bb3306d119cc777fa900ba034cd52"
HEAD=26372987
# 1) all events from the pool contract, last 60k blocks
cnt=collections.Counter()
for i in range(6):
    to=HEAD-i*10000; frm=to-9999
    logs=rpc("eth_getLogs",[{"address":POOL,"fromBlock":hex(frm),"toBlock":hex(to)}])
    for l in logs: cnt[(l['topics'][0], len(l['topics']))]+=1
print("pool-contract events 60k blocks:")
for k,v in cnt.most_common(12): print(' ', k[0][:18], 'ntop',k[1], v)
# 2) scout Harvest topic on CRV token, 60k blocks; control = burn event on pool (same window)
H='0x14a992338172c40df4462447b550ac77ef75340cb0caa286624f9ac44a7cdc23'
B='0xe2403640ba68fed3a2f88b7557551d1993f84b99bb10ff833f0cf8db0c5e0486'
for name,flt in [('Harvest topic on CRV', {"address":CRV,"topics":[H],"fromBlock":hex(HEAD-60000),"toBlock":hex(HEAD)}),
                 ('control burn event on pool', {"address":POOL,"topics":[B],"fromBlock":hex(HEAD-60000),"toBlock":hex(HEAD)})]:
    logs=rpc("eth_getLogs",[flt]); print(name, '->', len(logs) if logs is not None else 'ERR')
