import json,urllib.request,os
url=os.environ['RPC_RELAY_URL']; chain='ethereum'; lane='research'
def rpc(method,params):
    body=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    r=urllib.request.urlopen(url.rstrip('/')+'/'+chain+'?lane='+lane, body, timeout=30)
    return json.load(r)
addrs={
 'FeeBarn':'0xc59b0e4de5f1248c1140964e0ff287b192407e0c',
 'BatchAuct_v2cand':'0x61AaA90AB3169af8C0E2c0C2e822eE57676DFC8d',
 'BatchAuct_v1cand':'0xAEA4d0616135CDF98551A439682D5f842e69b09A',
 'USDC':'0xA0b86991c6218a36cC1cC64aC1F24553b9DBcf9d',
}
for n,a in addrs.items():
    r=rpc('eth_getCode',[a,'latest'])
    res=r.get('result') or ''
    print(n, len(res)//2, res[:14]+'...'+res[-8:])
