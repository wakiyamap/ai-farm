import json, urllib.request, os
URL=os.environ['RPC_RELAY_URL']
def rpc(method, params, chain='ethereum', lane='research'):
    body=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    req=urllib.request.Request(f"{URL}/{chain}?lane={lane}", data=body, headers={'content-type':'application/json'})
    return json.loads(urllib.request.urlopen(req, timeout=60).read())
POOL="0xcf50b810e57ac33b91dcf525c6ddd9881b139332"
def call(data,to=POOL):
    r=rpc("eth_call",[{"to":to,"data":data},"latest"]); return r.get('result',r)
GETTERS={
 'operator() ctrl':'0x570ca735',
 'rewardToken()':'0xf7c618c1',
 'minter()':'0x07546172',
 'harvestBonus()':'0x8ceb7b6f',
 'harvester()':'0x4bdaeac1',
 'harvesterBase()':'0x24a3cc10',
 'rewardForPriority()':'0x7ac77492',
 'harvestAll()':'0x8ed955b9',
}
for k,v in GETTERS.items():
    print(k.ljust(18), v, '->', call(v))
