import json, urllib.request, os
URL=os.environ['RPC_RELAY_URL']
def rpc(method, params, chain='ethereum', lane='research'):
    body=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    req=urllib.request.Request(f"{URL}/{chain}?lane={lane}", data=body, headers={'content-type':'application/json'})
    return json.loads(urllib.request.urlopen(req, timeout=60).read()).get('result')
def call(data, to="0xcf50b810e57ac33b91dcf525c6ddd9881b139332"):
    return rpc("eth_call",[{"to":to,"data":data},"latest"])
POOL="0xcf50b810e57ac33b91dcf525c6ddd9881b139332"
tests={
 'minter()':'0x06fd60c0',
 'harvestBonus()':'0x'+__import__('hashlib').sha256('harvestBonus()'.encode()).digest()[:4].hex(),
 'harvester()':'0x'+__import__('hashlib').sha256('harvester()'.encode()).digest()[:4].hex(),
 'harvesterBase()':'0x'+__import__('hashlib').sha256('harvesterBase()'.encode()).digest()[:4].hex(),
 'operator()':'0x'+__import__('hashlib').sha256('operator()'.encode()).digest()[:4].hex(),
 'rewardToken()':'0x'+__import__('hashlib').sha256('rewardToken()'.encode()).digest()[:4].hex(),
}
for k,s in tests.items():
    v=call(s)
    print(k, s, '->', v)
