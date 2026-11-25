import json, sys, os, urllib.request
URL=os.environ.get('RPC_RELAY_URL')
def call(chain, method, params, lane='research'):
    body=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    req=urllib.request.Request(f"{URL}/{chain}?lane={lane}", data=body, headers={"content-type":"application/json"})
    r=json.loads(urllib.request.urlopen(req, timeout=60).read())
    if 'error' in r: print('ERR', r['error'], file=sys.stderr)
    return r.get('result')
