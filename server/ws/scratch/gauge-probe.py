import json, urllib.request, os
URL=os.environ['RPC_RELAY_URL']
def rpc(method, params, chain='ethereum', lane='research'):
    body=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    req=urllib.request.Request(f"{URL}/{chain}?lane={lane}", data=body, headers={'content-type':'application/json'})
    return json.loads(urllib.request.urlopen(req, timeout=60).read())
GC="0xc45b9646c139dc5b80b9e9de440f6e6b1c119b53"  # gauge controller
def call(data,to): 
    r=rpc("eth_call",[{"to":to,"data":data},"latest"]); return r.get('result',r)
CRV="0xd533a949740bb3306d119cc777fa900ba034cd52"; CVX="0x4e3fbd56cd56c3e72c1403e103b45db9da5b9d2b"
r=call('0x8ed955b9' if False else '0x06fd60c0' if False else '0x166be73d', GC)  # getGauge(address)? check below
print('getGauge(CRV) raw ->', r)
