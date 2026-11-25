import json, urllib.request, os, subprocess
URL=os.environ['RPC_RELAY_URL']
def rpc(method, params, chain='ethereum', lane='research'):
    body=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    req=urllib.request.Request(f"{URL}/{chain}?lane={lane}", data=body, headers={'content-type':'application/json'})
    d=json.loads(urllib.request.urlopen(req, timeout=60).read())
    return d.get('result', ('error',d.get('error',{}).get('message')))
os.environ['PATH']='/opt/foundry/bin:'+os.environ['PATH']
def sel(sig): return '0x'+subprocess.run(['cast','keccak',sig],capture_output=True,text=True).stdout.strip().replace('0x','')[:8]
FEEDEP="0x8014595f2ab54cd7c604b00e9fb932176fdc86ae"
r=rpc("eth_call",[{"to":FEEDEP,"data":sel('vlcvx()')},"latest"]); print('FeeDeposit.vlcvx() ->', r)
VLCVX=r if isinstance(r,str) and r.startswith('0x000000000000000000000000') else None
addr="0x"+r[-40:] if r and r.startswith('0x') else None
print('vlcvx addr', addr)
for g in ['checkpoint()','distributionsFeesActive()','totalSupply()','name()','getDeadline()']:
    v=rpc("eth_call",[{"to":addr,"data":sel(g)},"latest"])
    print('vlcvx', g, '->', v if not isinstance(v,tuple) else v[1])
