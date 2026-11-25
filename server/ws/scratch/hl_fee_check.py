import json, os, urllib.request
URL = os.environ.get('RPC_RELAY_URL','').rstrip('/') + '/hyperevm?lane=scout'
def call(method, params):
    req = urllib.request.Request(URL, data=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode(), headers={"Content-Type":"application/json"})
    r = json.load(urllib.request.urlopen(req, timeout=60))
    if 'error' in r: return f"ERR {r['error].get('message') if False else r['error']}"
    return r['result']
