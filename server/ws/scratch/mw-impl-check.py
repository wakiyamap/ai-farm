import json, urllib.request, os
URL=os.environ['RPC_RELAY_URL']
def req(method,params):
    rq=urllib.request.Request(f"{URL}/base?lane=research",data=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode(),headers={"content-type":"application/json"})
    return json.loads(urllib.request.urlopen(rq,timeout=90).read())
IMPL="0x73d8a3bf62aaca6690791e57ebaee4e1d875d8fe"
r=req("eth_getCode",[IMPL,"latest"])
code=r['result']
print("impl code len", len(code)//2)
for sel in ["5ec88c79","d3894670","c40bb49b","d8739083","e3c47b04","5ec88c79"]:
    print(sel, "present" if sel in code else "absent")
# impl direct call
r=req("eth_call",[{"to":IMPL,"data":"0x5ec88c79"+"544784a56c889bcda2603c73ce1957f2b9133ec0"},"latest"])
print("impl direct:", r.get('result',r.get('error'))[:120])
