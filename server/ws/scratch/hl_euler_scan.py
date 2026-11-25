import json, os, urllib.request
URL = os.environ.get('RPC_RELAY_URL','').rstrip('/') + '/hyperevm?lane=scout'
def call(method, params):
    req = urllib.request.Request(URL, data=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode(), headers={"Content-Type":"application/json"})
    r = json.load(urllib.request.urlopen(req, timeout=120))
    if 'error' in r: return {"__err__": r['error']}
    return r['result']
vaults = json.load(open('scratch/hl_vaults.json'))
FROM, TO = hex(50905000), hex(51587598)
LIQ='0x8246cc71ab01533b5bebc672a636df812f10637ad720797319d5741d5ebb3962'
BORROW='0xcbc04eca7e9da35cb1393a6135a199ca52e450d5e9251cbd99f7847d33a36750'
out={}
for name,topic in (('liq',LIQ),('borrow_ctl',BORROW)):
    logs=[]
    for part in (vaults[:32], vaults[32:]):
        r=call('eth_getLogs',[{"address":part,"topics":[topic],"fromBlock":FROM,"toBlock":TO}])
        if isinstance(r,dict) and '__err__' in r: print(name,'ERR',r); break
        logs+=r
    out[name]=logs
    print(name, len(logs))
json.dump(out, open('scratch/hl_logs.json','w'))
# fee getters on 3 vaults
for v in vaults[:3]:
    for fn,sig in (('name','0x06fdde03'),('feeRecv','0xb3f00674'),('pfeeRecv','0x39a51be5'),('accFees','0xf6e50f58')):
        r=call('eth_call',[{"to":v,"data":sig},"latest"])
        print(v[:10],fn,r if not isinstance(r,str) else r[:130])
