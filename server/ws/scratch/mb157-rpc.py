import json, os, time, urllib.request
URL = os.environ.get('RPC_RELAY_URL', 'http://127.0.0.1:8545')
LANE = 'research'
def rpc(method, params, lane=None, tries=5):
    u = f"{URL}/base?lane={lane or LANE}"
    body = json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    last = None
    for i in range(tries):
        req = urllib.request.Request(u, data=body, headers={'content-type':'application/json'})
        j = json.loads(urllib.request.urlopen(req, timeout=30).read())
        if 'result' in j: return j['result']
        last = j.get('error')
        transient = last is not None and ('everted' in str(last) or str(last.get('code')) in ('-32000','-32005','-32603','3'))
        if not transient: break
        time.sleep(0.6)
    raise RuntimeError(f"{method} error: {last}")
def call(to, data, lane=None): return rpc('eth_call', [{"to":to,"data":data}, "latest"], lane)
