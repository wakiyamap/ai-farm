import json, urllib.request, os
url=os.environ['RPC_RELAY_URL']
WRAPS=[ "0xBfaE8C8500cD35B652373a3Ad5BaA0D604A05a29", # T+
        "0xB17EE7D061e076ff1aD6bd2141888CFb39C0Ccdc", # C+
        "0xD4E1CAF200b29585aADc9AF39c16D57C8c82EbF1"] # G+
MINT="0xf114ca9eb82947af39f957fa726280fd3d5d81c3d7635a4aeb5c302962856eba"
REDEEM="0x18fd144d7dbcbaa6f00fd47a84adc7dc3cc64a326ffa2dc7691a25e3837dba03"
def rpc(method, params):
    body=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    req=urllib.request.Request(url+"/ethereum?lane=research", data=body, headers={"content-type":"application/json"})
    return json.load(urllib.request.urlopen(req))['result']
from_block="0x67C74FB"  # 26349179
for name,topic in (("Mint",MINT),("Redeem",REDEEM)):
    logs=rpc("eth_getLogs",[{"address":WRAPS,"topics":[topic],"fromBlock":from_block,"toBlock":"0x67D31AB"}])
    print(name, len(logs))
    json.dump(logs, open(f"ov-{name}.json","w"))
