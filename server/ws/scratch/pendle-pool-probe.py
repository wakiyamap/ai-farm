import json, urllib.request, os
URL=os.environ["RPC_RELAY_URL"]; LANE=os.environ.get("RPC_LANE","research")
def call(method, params):
    body={"jsonrpc":"2.0","id":1,"method":method,"params":params}
    r=urllib.request.urlopen(URL.rstrip("/")+"/ethereum?lane="+LANE, json.dumps(body).encode(), timeout=30)
    j=json.loads(r.read())
    if "error" in j: return {"error": j["error"]}
    return j["result"]
def enc(sel, arg=None, pad=0):
    d="0x"+sel[2:]
    if arg: d+= "0"*(24-len(arg[2:]))+arg[2:] if len(arg)==42 else arg[2:]
    return d
POOL="0xf1f53912c156a8c06927746cb20ba11ecec526ce"
PT="0x65bc0a0cf38ecdfc95e553de01af01a56da225ce"
SY="0x31853542da976400fb66278be7a09636aad332fc"
out={}
for name,sel,extra in [("sy","0x181cc05b",None),("POOL_ID","0xe0d7d0e9"+"c3d63710c5b44e82095f2336f16bff7b807022b63da620a71868c6bc"[8:],None),
                       ("totalAssets","0x01e1d114",None),("getCacheIndex","0x35819b5f",None),("expiry","0xe184c9be",None),
                       ("reserves_SY","0xd66bd524"+"bff084d124daa1581c433cf2f8661c01ae1d0f28945bd3dcb886d3db"[8:],SY),
                       ("reserves_underlying","0xd66bd524bff084d124daa1581c433cf2f8661c01ae1d0f28945bd3dcb886d3db"[0:8],"PLACEHOLDER"),
                       ("getSwapAmountOut_pt","0x66b9ffac"+"452ca715816ae5cf59bd4409d33456bd2a5053ed525d423f05202938"[8:],PT),
                       ("underlying_SY","0x6f307dc3",None)]:
    to = SY if name=="underlying_SY" else POOL
    data=sel if extra is None else sel+"0"*(24-len(extra[2:]))+extra[2:]
    if extra=="PLACEHOLDER": continue
    out[name]=call("eth_call",[{"to":to,"data":data},"latest"])
json.dump(out,open("scratch/pendle-pool-probe.json","w"),indent=1)
print(json.dumps(out,indent=1)[:1500])
