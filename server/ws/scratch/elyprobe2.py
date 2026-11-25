import json, urllib.request, os
URL=os.environ['RPC_RELAY_URL']; LANE='research'
def rpc(m,p=None):
    b=json.dumps({"jsonrpc":"2.0","id":1,"method":m,"params":p or []}).encode()
    req=urllib.request.Request(f"{URL}/elysium?lane={LANE}",b,{"content-type":"application/json"})
    r=json.loads(urllib.request.urlopen(req,timeout=60).read())
    if 'error' in r: return ('ERR', json.dumps(r['error'])[:120])
    return ('OK', r['result'])
a="0x97796d80b6a1db78632f7451196b04f307329eb6"
st,r=rpc("eth_call",[{"to":a,"data":"0x3850c7bd"},"latest"]); print("slot0 full:", st, r)
st,r=rpc("eth_call",[{"to":a,"data":"0xdeadbeef"},"latest"]); print("garbage:", st, str(r)[:80])
st,r=rpc("eth_call",[{"to":a,"data":"0xfc0c546a"},"latest"]); print("token():", st, str(r)[:80])
st,c=rpc("eth_getCode",[a,"latest"]); print("code len:", len(c)//2 if st=="OK" else c)
