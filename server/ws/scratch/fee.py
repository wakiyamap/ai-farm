import json,urllib.request,os
url=os.environ['RPC_RELAY_URL']; chain='ethereum'; lane='research'
def rpc(method,params):
    body=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    r=urllib.request.urlopen(url.rstrip('/')+'/'+chain+'?lane='+lane, body, timeout=30)
    return json.load(r)
sel='0x0ab8afac'  # auctionContract()
r=rpc('eth_call',[{"to":"0xc59b0e4de5f1248c1140964e0ff287b192407e0c","data":sel},"latest"])
print('auctionContract:',r)
