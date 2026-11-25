import json, urllib.request, os, hashlib
URL=os.environ['RPC_RELAY_URL']
def rpc(method, params, chain='ethereum', lane='research'):
    body=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    req=urllib.request.Request(f"{URL}/{chain}?lane={lane}", data=body, headers={'content-type':'application/json'})
    return json.loads(urllib.request.urlopen(req, timeout=60).read()).get('result')
def sel(sig): return '0x'+hashlib.sha3_256(sig.encode(),512,b'===='.encode()).digest()[:4].hex() if False else '0x'+__import__('hashlib').sha256
POOL="0xcf50b810e57ac33b91dcf525c6ddd9881b139332"
def call(data,to=POOL):
    r=rpc("eth_call",[{"to":to,"data":data},"latest"]); return r
S={s:sel(s) for s in ['minter()','harvestBonus()','harvester()','harvesterBase()','operator()','rewardToken()','rewardForPriority()','rewardPoolDeposit(address,uint256)']}
for k,v in S.items(): print(k,v)
# positive control: operator() known selector 0x570ca735
print('operator ctrl:', call('0x570ca735'))
for k,v in S.items():
    print(k, '->', call(v))
