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
NEWF="0xc78bc588e970501432b2583ec1b6d2f4509b3b55"
out={}
out["pool_getPoolId"]=call("eth_call",[{"to":POOL,"data":"0x38fff2d0"},"latest"])
out["newf_code_len"]=len(str(call("eth_getCode",[NEWF,"latest"])))
out["newf_reserves_SY"]=call("eth_call",[{"to":NEWF,"data":"0xd66bd524"+"0"*(24-len(SY[2:]))+SY[2:]},"latest"])
out["newf_getSwapAmountOut_pt"]=call("eth_call",[{"to":NEWF,"data":"0x66b9ffac"+"0"*(24-len(PT[2:]))+PT[2:]+"0"*24+"0"*15+"346dc5d6388f770000000000000000000000000000000000000000000000"[24:]},"latest"])
json.dump(out,open("scratch/pendle-probe5.json","w"),indent=1)
print(json.dumps(out,indent=1)[:1200])
