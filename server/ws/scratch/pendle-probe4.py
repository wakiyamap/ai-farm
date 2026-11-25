import json, urllib.request, os
URL=os.environ["RPC_RELAY_URL"]; LANE=os.environ.get("RPC_LANE","research")
def call(method, params):
    body={"jsonrpc":"2.0","id":1,"method":method,"params":params}
    r=urllib.request.urlopen(URL.rstrip("/")+"/ethereum?lane="+LANE, json.dumps(body).encode(), timeout=30)
    j=json.loads(r.read())
    if "error" in j: return {"error": j["error"]}
    return j["result"]
POOL="0xf1f53912c156a8c06927746cb20ba11ecec526ce"
SY="0x31853542da976400fb66278be7a09636aad332fc"
PT="0x65bc0a0cf38ecdfc95e553de01af01a56da225ce"
SCALE="0x5584f42b4f3c257512dbe147c15bf17eaf4cee50"
out={}
out["scale_code_len"]=len(str(call("eth_getCode",[SCALE,"latest"])))
for name,sel,to,arg in [
  ("symbol","0x95d89b41",SY,None),
  ("decimals","0x36e74b6b",SY,None),
  ("getPoolId","0x"+ "9e01574170000000000000000000000000000000000000000000000000000000"[0:8],POOL,None),
]: out[name]=call("eth_call",[{"to":to,"data":sel},"latest"])
json.dump(out,open("scratch/pendle-probe4.json","w"),indent=1)
print(json.dumps(out,indent=1))
