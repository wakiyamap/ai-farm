import json, urllib.request, os, subprocess
URL=os.environ['RPC_RELAY_URL']
def rpc(method, params, chain='ethereum', lane='research'):
    body=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    req=urllib.request.Request(f"{URL}/{chain}?lane={lane}", data=body, headers={'content-type':'application/json'})
    d=json.loads(urllib.request.urlopen(req, timeout=60).read())
    return d.get('result', d.get('error',{}).get('message'))
import os
os.environ['PATH']='/opt/foundry/bin:'+os.environ['PATH']
def kc(sig): return subprocess.run(['cast','keccak',sig],capture_output=True,text=True).stdout.strip().replace('0x','')[:8]
CRV="0xd533a949740bb3306d119cc777fa900ba034cd52"; CVX="0x4e3fbd56cd56c3e72c1403e103b45db9da5b9d2b"
CVXCRV="0x62b9c7356a2dc64a1969e19c23e4f579f9810aa7"; FEED="0x8014595f2ab54cd7c604b00e9fb932176fdc86ae"
GET=['harvestBonus()','harvester()','harvesterBase()','minter()','harvest()','totalSupply()']
for tok,name in [(CRV,'CRV'),(CVX,'CVX'),(CVXCRV,'cvxCrv'),(FEED,'FeeDeposit')]:
    for g in GET:
        r=rpc("eth_call",[{"to":tok,"data":kc(g)},"latest"])
        ok = (isinstance(r,str) and r.startswith('0x'))
        print(name, g, '->', 'OK '+r[:26] if ok else 'revert')
        if g=='totalSupply()' and ok: break
