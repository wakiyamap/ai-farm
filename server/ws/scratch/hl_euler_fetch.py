import json, os, urllib.request
URL = os.environ.get('RPC_RELAY_URL','').rstrip('/') + '/hyperevm?lane=scout'
def call(method, params):
    req = urllib.request.Request(URL, data=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode(), headers={"Content-Type":"application/json"})
    r = json.load(urllib.request.urlopen(req, timeout=60))
    if 'error' in r: raise SystemExit(f"ERR {method}: {r['error']}")
    return r['result']
FACT='0xcF5552580fD364cdBBFcB5Ae345f75674c59273A'
vaults=[]
for i in range(60):
    d='0x378cdb62'+format(i,'064x')
    r=call('eth_call',[{"to":FACT,"data":d},"latest"])
    vaults.append('0x'+r[-40:])
print(json.dumps(vaults))
