import json,urllib.request,os
url=os.environ["RPC_RELAY_URL"]+"/ethereum?lane=research"
SEL={"asset":"0x38d52e0f","decimals":"0x313ce567","maxLTV":"0xf384bd05","dirtyLiquidationFee":None}
def call(to,sig):
    d={"jsonrpc":"2.0","id":1,"method":"eth_call","params":[{"to":to,"data":sig},"latest"]}
    req=urllib.request.Request(url,data=json.dumps(d).encode(),headers={"content-type":"application/json"})
    r=json.loads(urllib.request.urlopen(req,timeout=15).read())
    if "error" in r: return None
    return r["result"]
bor=json.load(open("scratch/frax-borrows.json"))
rows=[]
for addr,_ in bor[:10]:
    a=call(addr,"0x38d52e0f"); d=call(addr,"0x313ce567"); m=call(addr,"0xf384bd05")
    rows.append([addr,(a or "revert")[-40:],d and int(d,16),m and int(m,16)])
for r in rows: print(r)
