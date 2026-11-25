import json,urllib.request,os
url=os.environ['RPC_RELAY_URL']+'/optimism?lane=research'
def raw(m,p):
    req=urllib.request.Request(url,data=json.dumps({"jsonrpc":"2.0","id":1,"method":m,"params":p}).encode(),headers={'content-type':'application/json'})
    return json.loads(urllib.request.urlopen(req,timeout=60).read())
def call(P,sel):
    rr=raw('eth_call',[{"to":P,"data":sel},"latest"])
    return rr.get('result') if 'result' in rr else 'ERR:'+rr.get('error',{}).get('message','?')[:40]
def code(P):
    return len(raw('eth_getCode',[P,'latest'])['result'])//2
for P in ['0x394a9fcbab8599437d9ec4e5a4a0eb7cb1fd2f69','0x47029bc8f5cbe3b464004e87ef9c9419a48018cd','0x5520385bfcf07ec87c4c53a7d8d65595dff69fa4']:
    print(P,'code bytes',code(P))
    for sel,name in [('0xc45a0155','factory()'),('0x38592901','slot0()'),('0x357797ba','fee()'),('0x023c9935','token0()')]:
        print(' ',name,call(P,sel)[:80])
