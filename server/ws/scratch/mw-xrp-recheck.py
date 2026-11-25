import json, urllib.request, os
URL=os.environ['RPC_RELAY_URL']
CMP="0xfbb21d0380bee3312b33c4353c8936a0f13ef26c"
BORROWER="0x544784a56c889bcda2603c73ce1957f2b9133ec0"
def call(block):
    data="0x5ec88c79"+BORROWER[2:]
    p={"jsonrpc":"2.0","id":1,"method":"eth_call","params":[{"to":CMP,"data":data},hex(block)]}
    rq=urllib.request.Request(f"{URL}/base?lane=research",data=json.dumps(p).encode(),headers={"content-type":"application/json"})
    return json.loads(urllib.request.urlopen(rq,timeout=90).read())
def dec(res):
    hexs=res[2:]; words=[int(hexs[i:i+64],16) for i in range(0,len(hexs),64)]
    liq,sf=words[0],words[1]
    top= (liq>>255)&1
    liqdec=(liq-(1<<255))/1e18 if top else liq/1e18
    return f"liquidity={liqdec:.2f} USD shortfall={sf/1e18:.2f} USD -> {'LIQUIDATABLE' if (not top and sf>0) else 'HEALTHY'}"
for label,B in [("capture3-1=55160601",55160601),("capture3-131072=55029530",55029530),("capture1-1=54911220",54911220),("control healthy 54700000",54700000),("control healthy 53800000",53800000)]:
    r=call(B)
    if 'error' in r: print(label,"ERR",r['error']); continue
    print(label, dec(r['result']))
