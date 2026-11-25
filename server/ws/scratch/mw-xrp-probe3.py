import json, urllib.request, os
URL=os.environ['RPC_RELAY_URL']
def req(p):
    rq=urllib.request.Request(f"{URL}/base?lane=research",data=json.dumps(p).encode(),headers={"content-type":"application/json"})
    return json.loads(urllib.request.urlopen(rq,timeout=90).read())
CMP="0xfbb21d0380bee3312b33c4353c8936a0f13ef26c"
r=req({"jsonrpc":"2.0","id":1,"method":"eth_getCode","params":[CMP,"latest"]})
print("code len", len(r['result']) if 'result' in r else r.get('error'), r['result'][:60] if 'result' in r else "")
