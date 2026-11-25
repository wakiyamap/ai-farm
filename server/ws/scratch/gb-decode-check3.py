import json, urllib.request
RELAY="http://127.0.0.1:8545"
def rpc(chain, lane, method, params, timeout=40):
    body=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    req=urllib.request.Request(f"{RELAY}/{chain}?lane={lane}",data=body,headers={"content-type":"application/json"})
    j=json.loads(urllib.request.urlopen(req,timeout=timeout).read())
    if "error" in j: raise SystemExit(f"error: {j['error']}")
    return j["result"]
CM='0x1293a69e4ad4a93293a06b6303104be35bdd83af'
COMP='0x81cb9ea2d59414ab13ec0567efb09767ddbe897a'
TARGET='56631dcb1ea548d2629e82e01375090ed1f81b7e'
SEL='3b007fb9'
def enc_cm(offset,size):
    return '0x'+SEL+CM[2:].lower().rjust(64,'0')+hex(offset)[2:].rjust(64,'0')+hex(size)[2:].rjust(64,'0')
ret=rpc('ethereum','research','eth_call',[{"to":COMP,"data":enc_cm(0,100)},'0x'+hex(26287069)[2:]])
b=ret[2:]
words=[b[i:i+64] for i in range(0,len(b),64)]
print("total words:", len(words))
for i,w in enumerate(words[:26]): print(i, w[:64])
pos=b.find(TARGET)
print("TARGET hex-char pos", pos, "word", pos//64, "aligned:", pos%64==24)
