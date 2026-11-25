"""Read-only relay helper (research lane). usage: rc_rpc.py <chain> <method> '<json params>'"""
import json, os, sys, urllib.request
chain, method, params = sys.argv[1], sys.argv[2], json.loads(sys.argv[3])
url = os.environ['RPC_RELAY_URL'].rstrip('/') + '/' + chain + '?lane=research'
body = json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params}).encode()
req = urllib.request.Request(url, data=body, headers={'content-type': 'application/json'})
print(urllib.request.urlopen(req, timeout=30).read().decode())
