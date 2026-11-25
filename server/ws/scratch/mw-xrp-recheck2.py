import json, urllib.request, os
URL=os.environ['RPC_RELAY_URL']
CMP="0xfbb21d0380bee3312b33c4353c8936a0f13ef26c"
BORROWER="0x544784a56c889bcda2603c73ce1957f2b9133ec0"
FROM="0x0000000000000000000000000000000000000000"
def req(method,params):
    rq=urllib.request.Request(f"{URL}/base?lane=research",data=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode(),headers={"content-type":"application/json"})
    return json.loads(urllib.request.urlopen(rq,timeout=90).read())
def gal(block):
    r=req("eth_call",[{"from":FROM,"to":CMP,"data":"0x5ec88c79"+BORROWER[2:]},block])
    if 'error' in r: return "ERR "+json.dumps(r['error'])[:80]
    res=r['result']; hexs=res[2:]; w=[int(hexs[i:i+64],16) for i in range(0,len(hexs),64)]
    top=(w[0]>>255)&1
    if top: return f"HEALTHY liquidity={(w[0]-(1<<255))/1e18:.2f}"
    return f"{'LIQUIDATABLE' if w[1]>0 else 'flat'} shortfall={w[1]/1e18:.2f} USD"
for label,B in [("capture3-1 (55160601)",55160601),("capture3-131072 (55029530)",55029530),("capture2-1 (54922326)",54922326),("capture1-1 (54911220)",54911220),("capture1-131072 (54780149)",54780149),("ctrl healthy 54700000",54700000),("ctrl healthy 53800000",53800000)]:
    print(label, gal(hex(B)))
