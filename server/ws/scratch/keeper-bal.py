import json, urllib.request, os, subprocess
URL=os.environ['RPC_RELAY_URL']
def rpc(method, params, chain='ethereum', lane='research'):
    body=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    req=urllib.request.Request(f"{URL}/{chain}?lane={lane}", data=body, headers={'content-type':'application/json'})
    d=json.loads(urllib.request.urlopen(req, timeout=60).read())
    return d.get('result', d.get('error',{}).get('message'))
import os
os.environ['PATH']='/opt/foundry/bin:'+os.environ['PATH']
def sel(sig): return subprocess.run(['cast','keccak',sig],capture_output=True,text=True).stdout.strip().replace('0x','')[:8]
KEEP="0xa88e98bbd2af6ddd642407cb5455f956f0c553f0"
SECC="0x7e79a8173b3f63395d6a59f8ca4af214c29d359b"
CVXCRV="0x62b9c7356a2dc64a1969e19c23e4f579f9810aa7"; CVX="0x4e3fbd56cd56c3e72c1403e103b45db9da5b9d2b"
POOL="0xcf50b810e57ac33b91dcf525c6ddd9881b139332"
HEAD=26372987
def bal(tok,who,blk):
    r=rpc("eth_call",[{"to":tok,"data":'0x'+sel('balanceOf(address)')+'0'*24+who[2:]},"latest"]) if blk=='latest' else \
      rpc("eth_call",[{"to":tok,"data":'0x'+sel('balanceOf(address)')+'0'*24+who[2:]},hex(blk)])
    return int(r,16)/1e18 if isinstance(r,str) and r.startswith('0x') else r
for name,who in [('keeper',KEEP),('secEOA',SECC)]:
    for tok,tname in [(CVXCRV,'cvxCrv'),(CVX,'CVX')]:
        b0=bal(tok,who,'latest'); b1=bal(tok,who,HEAD-100000)
        print(name,tname,'now',b0,'100k-blocks-ago',b1, 'delta', (b0-b1) if isinstance(b0,float) and isinstance(b1,float) else '')
# pool pending rewards for keeper account
r=rpc("eth_call",[{"to":POOL,"data":'0x'+sel('earned(address)')+ '0'*24+KEEP[2:]},"latest"]); print('keeper earned() ->', r)
