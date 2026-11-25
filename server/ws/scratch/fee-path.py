import json, urllib.request, os, subprocess
URL=os.environ['RPC_RELAY_URL']
def rpc(method, params, chain='ethereum', lane='research'):
    body=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    req=urllib.request.Request(f"{URL}/{chain}?lane={lane}", data=body, headers={'content-type':'application/json'})
    d=json.loads(urllib.request.urlopen(req, timeout=60).read())
    return d.get('result', 'ERR:'+str(d.get('error',{}).get('message')))
os.environ['PATH']='/opt/foundry/bin:'+os.environ['PATH']
def sel(sig): return '0x'+subprocess.run(['cast','keccak',sig],capture_output=True,text=True).stdout.strip().replace('0x','')[:8]
def call(to,g):
    v=rpc("eth_call",[{"to":to,"data":sel(g)},"latest"]); return v
BOOST="0xf403c135812408bfbe8713b5a23a04b3d48aae31"
REGISTRY="0xC0ed8E9C9B71F189167144d1aA4469a72Bd1949a"  # pinned? not yet - only use if controls ok
HEAD=26372987
print('booster feeDistro() ->', call(BOOST,'feeDistro()'))
print('booster feeManager() ->', call(BOOST,'feeManager()'))
print('booster feeToken() ->', call(BOOST,'feeToken()'))
blk=rpc("eth_getBlockByNumber",[hex(HEAD),False]); print('head ts', int(blk['timestamp'],16) if blk and 'timestamp' in blk else blk, 'block', HEAD)
import time; print('now', int(time.time()))
