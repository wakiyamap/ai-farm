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
FROM,TO="0x1920e7b","0x19283ab"
for name,topic in (("Mint",MINT),("Redeem",REDEEM)):
    logs=rpc("eth_getLogs",[{"address":WRAPS,"topics":[topic],"fromBlock":FROM,"toBlock":TO}])
    print(name, len(logs)); json.dump(logs, open(f"ov2-{name}.json","w"))
logs=rpc("eth_getLogs",[{"address":WRAPS,"fromBlock":FROM,"toBlock":TO}])
print("no-topic wrap logs:", len(logs)); json.dump(logs, open("ov2-any.json","w"))
c=rpc("eth_call",[{"to":WRAPS[0],"data":"0x18160d92"},"latest"]); print("T+ supply:", int(c,16)/1e6)
c=rpc("eth_call",[{"to":WRAPS[1],"data":"0x18160d92"},"latest"]); print("C+ supply:", int(c,16)/1e6)
c=rpc("eth_call",[{"to":WRAPS[2],"data":"0x18160d92"},"latest"]); print("G+ supply:", int(c,16)/1e6)
us=rpc("eth_getLogs",[{"address":[USDC],"fromBlock":FROM,"toBlock":TO}])
print("USDC control:", len(us))
