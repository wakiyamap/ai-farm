import json, urllib.request, os, subprocess
URL=os.environ['RPC_RELAY_URL']
def rpc(method, params, chain='ethereum', lane='research'):
    body=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    req=urllib.request.Request(f"{URL}/{chain}?lane={lane}", data=body, headers={'content-type':'application/json'})
    d=json.loads(urllib.request.urlopen(req, timeout=60).read())
    return d.get('result', 'ERR:'+str(d.get('error',{}).get('message')))
os.environ['PATH']='/opt/foundry/bin:'+os.environ['PATH']
def sel(sig): return '0x'+subprocess.run(['cast','keccak',sig],capture_output=True,text=True).stdout.strip().replace('0x','')[:8]
CAND="0xb576491f1e6e5e62f1d8f26062ee822b40b0e0d4"
for g in ['name()','totalSupply()','symbol()','decimals()','checkpoint()','distributionsFeesActive()','distributionsIncentive()','getForLockers(address)','lockers(uint256)']:
    v=rpc("eth_call",[{"to":CAND,"data":sel(g)},"latest"])
    ok=isinstance(v,str) and v.startswith('0x') and len(v)>=66
    print('candidate', g, '->', (v[:80]+'...' if ok else v))
