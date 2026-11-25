import json, urllib.request as u, os
url=os.environ['RPC_RELAY_URL']
WRAPS=[ "0xBfaE8C8500cD35B652373a3Ad5BaA0D604A05a29","0xB17EE7D061e076ff1aD6bd2141888CFb39C0Ccdc","0xD4E1CAF200b29585aADc9AF39c16D57C8c82EbF1"]
MINT="0xf114ca9eb82947af39f957fa726280fd3d5d81c3d7635a4aeb5c302962856eba"
REDEEM="0x18fd144d7dbcbaa6f00fd47a84adc7dc3cc64a326ffa2dc7691a25e3837dba03"
USDC="0xA0b86991c6218a36c19806a52ac31845e847f69a"
def rpc(method, params):
    body=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    req=u.Request(url+"/ethereum?lane=research", data=body, headers={"content-type":"application/json"})
    d=json.load(u.urlopen(req))
    if 'error' in d: print('ERR', d['error']); return None
    return d['result']
pages=[(26343179,26351178),(26351179,26359178),(26359179,26367178),(26367179,26375178),(26375179,26379178)]
def scan(label, filter_base, addr):
    total=[]
    for f,t in pages:
        r=rpc("eth_getLogs",[dict(filter_base, address=addr, fromBlock=hex(f), toBlock=hex(t))])
        if r is None: print(label,'FAILED page'); return None
        total+=r
    print(label, len(total))
    return total
any_=scan("any-log", {}, WRAPS)
mint=scan("Mint", {"topics":[MINT]}, WRAPS)
redeem=scan("Redeem", {"topics":[REDEEM]}, WRAPS)
usdc=scan("USDC control", {}, [USDC])
json.dump(any_, open("ov3-any.json","w")); json.dump(mint, open("ov3-mint.json","w")); json.dump(redeem, open("ov3-redeem.json","w"))
