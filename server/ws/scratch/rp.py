import json, sys, urllib.request, os
chain, params, method = sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv)>3 else 'eth_call'
url = os.environ['RPC_RELAY_URL']
lane = os.environ.get('LANE','research')
body = json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":json.loads(params)})
req = urllib.request.Request(f"{url}/{chain}?lane={lane}", data=body.encode(), headers={'content-type':'application/json'})
r = json.loads(urllib.request.urlopen(req, timeout=60).read())
print(json.dumps(r.get('result') if 'result' in r else r)[:int(os.environ.get('TRUNC','200'))])
