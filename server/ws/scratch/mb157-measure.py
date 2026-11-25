import json, os, sys, urllib.request
URL = os.environ.get('RPC_RELAY_URL','http://127.0.0.1:8545')
LANE = os.environ.get('RPC_LANE','research')
import time
def rpc(method, params, lane=None, tries=4):
    u = f"{URL}/base?lane={lane or LANE}"
    req = urllib.request.Request(u, data=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode(), headers={'content-type':'application/json'})
    j = json.loads(urllib.request.urlopen(req, timeout=30).read())
    if 'error' in j and tries>1 and 'everted' in str(j['error']):
        time.sleep(0.4); return rpc(method, params, lane, tries-1)
    return j['result']
def call(to, data, lane=None):
    return rpc('eth_call', [{"to":to,"data":data}, "latest"], lane)
if __name__ == '__main__':
    print(json.dumps(rpc(sys.argv[1], json.loads(sys.argv[2]) if len(sys.argv)>2 else [])))
