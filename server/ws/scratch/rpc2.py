import json, sys, urllib.request, os
chain = sys.argv[1]; method = sys.argv[2]; params = json.loads(sys.argv[3]) if len(sys.argv)>3 else []
out = sys.argv[4] if len(sys.argv)>4 else None
url = os.environ['RPC_RELAY_URL']; lane = os.environ.get('LANE','research')
body = json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params})
req = urllib.request.Request(f"{url}/{chain}?lane={lane}", data=body.encode(), headers={'content-type':'application/json'})
r = json.loads(urllib.request.urlopen(req, timeout=120).read())
if 'error' in r: print('ERROR', json.dumps(r['error'])[:300]); sys.exit(1)
if out: open(out,'w').write(json.dumps(r['result']))
else: print(json.dumps(r['result'])[:500])
