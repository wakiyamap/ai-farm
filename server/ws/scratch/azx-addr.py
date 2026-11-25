import json,urllib.request,os
RELAY=os.environ['RPC_RELAY_URL']
def call(chain,lane,method,params):
    data=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    with urllib.request.urlopen(f"{RELAY}/{chain}?lane={lane}",data,timeout=60) as r:
        d=json.loads(r.read())
    if 'error' in d: raise RuntimeError(json.dumps(d['error'])[:300])
    return d['result']
USDC="0xaf88d065e77c8cC2239327F5ED83A6aB0A91b106"
sym=call('arbitrum','research','eth_call',[{"to":USDC,"data":"0x95d89b02"},"latest"])
print('symbol', bytes.fromhex(sym[2:]).decode())
name=call('arbitrum','research','eth_call',[{"to":USDC,"data":"0x06fdde03"},"latest"])
print('name', bytes.fromhex(name[2:]).decode(errors="ignore"))
dec=call('arbitrum','research','eth_call',[{"to":USDC,"data":"0x313ce567"},"latest"])
print('decimals', int(dec,16))
