import json, urllib.request, os
URL=os.environ['RPC_RELAY_URL']
CMP="0xfbb21d0380bee3312b33c4353c8936a0f13ef26c"
BORROWER="0x544784a56c889bcda2603c73ce1957f2b9133ec0"
def req(p):
    rq=urllib.request.Request(f"{URL}/base?lane=research",data=json.dumps(p).encode(),headers={"content-type":"application/json"})
    return json.loads(urllib.request.urlopen(rq,timeout=90).read())
def show(tag, params):
    r=req({"jsonrpc":"2.0","id":1,"method":"eth_call","params":params})
    if 'error' in r: print(tag,"ERR",json.dumps(r['error'])[:160])
    else: print(tag, r['result'][:192])
show("latest plain", [{"to":CMP,"data":"0x5ec88c79"+BORROWER[2:]},"latest"])
show("latest with from", [{"from":"0x544784a56c889bcda2603c73ce1957f2b9133ec0","to":CMP,"data":"0x5ec88c79"+BORROWER[2:]},"latest"])
show("tag 0x14ef60b5(55160601)", [{"to":CMP,"data":"0x5ec88c79"+BORROWER[2:]},"0x14ef60b5"])
show("BN", [{"to":CMP,"data":"0x6fbd0065"},[]])  # not used, placeholder
r=req({"jsonrpc":"2.0","id":1,"method":"eth_blockNumber","params":[]}); print("head", int(r['result'],16))
